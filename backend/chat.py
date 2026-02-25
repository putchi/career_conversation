import json
import os
from io import BytesIO

import openai
import requests
from agents import trace
from agents.tracing import generation_span
from openai import OpenAI
from pypdf import PdfReader

from backend.tools import push, record_user_details, record_unknown_question, tools, set_openai_client, check_question_similarity, set_session_id

ME_DIR = os.environ.get("ME_DIR", "me")
_SANITY_API_VERSION = "2021-06-07"


class Me:
    def __init__(self) -> None:
        self.openai = OpenAI()
        set_openai_client(self.openai)
        project_id = os.environ.get("SANITY_PROJECT_ID")
        if project_id:
            self._load_from_sanity(project_id)
        else:
            self._load_from_files()

    def _load_from_sanity(self, project_id: str) -> None:
        dataset = os.environ.get("SANITY_DATASET", "production")
        query = (
            '*[_type == "profile"][0]{'
            'name, title, linkedinUrl, websiteUrl, suggestions, summary, model,'
            '"profilePdfUrl": profilePdf.asset->url,'
            '"referencePdfUrl": referencePdf.asset->url'
            "}"
        )
        url = f"https://{project_id}.api.sanity.io/v{_SANITY_API_VERSION}/data/query/{dataset}"
        response = requests.get(url, params={"query": query})
        response.raise_for_status()
        doc = response.json()["result"]

        self.name = doc["name"]
        self.title = doc["title"]
        self.linkedin_url = doc["linkedinUrl"]
        self.website_url = doc.get("websiteUrl") or ""
        self.suggestions = doc.get("suggestions") or []
        self.summary = doc["summary"]
        self.model = doc.get("model") or "gpt-4.1-mini"

        pdf_response = requests.get(doc["profilePdfUrl"])
        pdf_response.raise_for_status()
        pdf_bytes = pdf_response.content
        self.profile = "".join(
            p.extract_text() or "" for p in PdfReader(BytesIO(pdf_bytes)).pages
        )

        ref_url = doc.get("referencePdfUrl")
        if ref_url:
            ref_response = requests.get(ref_url)
            ref_response.raise_for_status()
            ref_bytes = ref_response.content
            self.ref_letter = "".join(
                p.extract_text() or "" for p in PdfReader(BytesIO(ref_bytes)).pages
            )
        else:
            self.ref_letter = ""

    def _load_from_files(self) -> None:
        self.name = os.environ.get("OWNER_NAME", "")
        self.title = os.environ.get("OWNER_TITLE", "")
        self.linkedin_url = os.environ.get("LINKEDIN_URL", "")
        self.website_url = os.environ.get("WEBSITE_URL", "")
        raw = os.environ.get("SUGGESTIONS", "")
        self.suggestions = [s.strip() for s in raw.split("|") if s.strip()]

        reader = PdfReader(f"{ME_DIR}/profile.pdf")
        self.profile = "".join(p.extract_text() or "" for p in reader.pages)

        try:
            reader = PdfReader(f"{ME_DIR}/reference_letter.pdf")
            self.ref_letter = "".join(p.extract_text() or "" for p in reader.pages)
        except FileNotFoundError:
            self.ref_letter = ""

        with open(f"{ME_DIR}/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

    def system_prompt(self) -> str:
        intro = (
            f"You are acting as {self.name}. "
            f"You are answering questions on {self.name}'s website, particularly questions related to "
            f"{self.name}'s career, background, skills and experience. "
            f"Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. "
            f"You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. "
            "Your audience may be potential clients, employers, or collaborators."
        )

        intent_dedup = (
            "DUPLICATE INTENT RULE: Before responding, scan the last 10 user messages in the conversation history. "
            "Determine the underlying intent of the current question — what information category is the user seeking? "
            "Two questions share the same intent if they ask for the same underlying information, even if: "
            "the phrasing changes, the scope changes (broader or narrower), the example changes, or the timeframe changes. "
            "Do NOT treat as duplicates if: the topic changes materially, the requested action changes materially, "
            "or the user adds a constraint that would change what a correct answer contains. "
            "When a duplicate intent is detected: respond naturally without acknowledging the similarity. "
            "Do not say 'this is the same question', 'you already asked', or reference previous phrasing in any way. "
            "Instead, reply more casually and more concisely than you would for a first answer. "
            "If it feels natural, use a brief bridging phrase (e.g. 'Yeah, mostly...' or 'Same deal, basically...') rather than repeating the full explanation. "
            "Do not call any tools when a duplicate is detected."
        )

        scope = (
            f"STRICT SCOPE RULE: You ONLY answer questions directly related to {self.name}'s professional background, "
            "career, skills, experience, projects, education, and work-related topics. "
            "If a question is unrelated to these topics — even if you know the answer — you must politely decline and redirect. "
            "IMPORTANT: Before sending your refusal, you MUST first call the record_unknown_question tool "
            "with the user's exact question. Only after the tool call completes should you send your refusal response. "
            "For example, if asked about general trivia, current events, other people, or any topic unrelated to the professional context, "
            f"respond with something like: 'That's a bit outside my expertise here! I'm best placed to talk about my own background and experience. "
            "Is there anything about my work or career I can help you with?' "
            "Never answer off-topic questions, no matter how simple or harmless they seem."
        )

        tool_instructions = (
            "For any question you cannot answer — whether on-topic but unknown, or outside the professional scope — "
            "you MUST first call check_question_similarity, then act on its result: "
            "if already_recorded is true, skip record_unknown_question and acknowledge the repeat "
            "(e.g. 'It looks like you already asked something similar — I've already noted it. "
            "Would you like to rephrase or clarify?'); "
            "if already_recorded is false, call record_unknown_question before sending your response. "
            f"When a user expresses interest in contacting {self.name} or working together: "
            "warmly invite them to share their name and email, and mention LinkedIn as an easy alternative in the same breath "
            f"(e.g. 'Feel free to drop your email here — or connect directly via LinkedIn: {self.linkedin_url}'). "
            "Do NOT call record_user_details until the user has actually provided an email address. "
            "Once they provide their email, call record_user_details exactly once per conversation. "
            "If the user asks whether their details were received (e.g. 'Did you get my email?', "
            "'Will someone contact me?', 'Just checking you got that') — do NOT call record_user_details. "
            "Look for an earlier assistant message confirming the details were recorded and confirm that instead. "
            'If record_user_details returns {"recorded": "ok"}: '
            f"confirm warmly that {self.name} has been notified and will be in touch, and mention LinkedIn. "
            'If record_user_details returns {"recorded": "already_recorded"}: '
            f"tell them their details are already on file and {self.name} will be in touch. "
            'If record_user_details returns {"recorded": "corrected"}: '
            "acknowledge the updated email briefly, e.g. 'Got it — I've updated your email.' "
            'If record_user_details returns {"recorded": "suspicious"}: '
            f"politely decline: 'I'm not able to record additional contact details at this time. "
            f"Please reach out directly via LinkedIn: {self.linkedin_url}' "
            'If record_user_details returns {"recorded": "already_overridden"}: '
            f"explain the session limit: 'It looks like the override was already used in this session. "
            f"Please reach out directly via LinkedIn: {self.linkedin_url}' "
            "Pass override=True ONLY when the user explicitly requests to replace a previously recorded email "
            "(e.g. 'please ignore my previous email and use this new one'). "
            "Never use override=True for first-time recordings or routine confirmations."
        )

        ref_section = f"\n\n## Reference Letter:\n{self.ref_letter}" if self.ref_letter else ""
        context = (
            f"## Summary:\n{self.summary}\n\n"
            f"## Profile:\n{self.profile}"
            f"{ref_section}"
        )

        behaviour = (
            f"With this context, please chat with the user. Always stay in character as {self.name}. "
            "You are a real person replying in a direct message - not a resume, a marketing page, or an AI assistant. "
            "Default to under 120 words unless the user explicitly asks for detail. "
            "Keep responses to 2 to 5 sentences by default. "
            "No bullet lists unless the user asks for a breakdown. "
            "No bold text, no structured sections like 'Experience' or 'Skills'. "
            "No corporate or polished marketing language. "
            "No generic closing questions like 'How can I help you?' "
            "Sound like someone replying on LinkedIn — natural, direct, conversational. "
            "If a question is broad, answer briefly and offer to expand rather than giving a full answer upfront. "
            "When introducing yourself, summarise in a few natural sentences relevant to what the user asked — do not list credentials. "
            "Prefer sounding helpful over sounding impressive. "
            "Never include meta-commentary - do not explain question similarity, scope differences, intent detection, or system behaviour. "
            "Do not reference previous phrasing or say things like 'you asked this before' or 'similar ground'. "
            "It is okay to be slightly informal. Use natural transitions like someone typing in chat."
        )

        output_rules = (
            "GLOBAL OUTPUT RULE: "
            'The Unicode character "\u2014" (em-dash) is strictly forbidden. '
            "Do not generate this character under any circumstance. "
            "Before returning a response, perform a self-check: "
            'if "\u2014" appears anywhere in your output, rewrite the entire response without it. '
            "Replace it with a period, comma, or regular hyphen. "
            "This is a hard constraint and overrides all stylistic or tone instructions."
        )

        privacy = (
            "PRIVACY RULE: Never disclose any personal contact details, including email address, phone number, "
            "home address, age, or personal ID — under no circumstances even if the user insists. "
            "If a visitor asks for any of these, steer them towards LinkedIn and ask for their name and email, "
            'then respond with: "I\'d love to connect! Please reach out to me via LinkedIn: https://linkedin.com/in/alexrabinovichpro"'
        )

        return "\n\n".join([intro, intent_dedup, scope, tool_instructions, context, behaviour, output_rules, privacy])

    def handle_tool_call(self, tool_calls) -> list[dict]:
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool_fn = {
                "record_user_details": record_user_details,
                "record_unknown_question": record_unknown_question,
                "check_question_similarity": check_question_similarity,
            }.get(tool_name)
            result = tool_fn(**arguments) if tool_fn else {}
            results.append({
                "role": "tool",
                "content": json.dumps(result),
                "tool_call_id": tool_call.id,
            })
        return results

    def chat(self, message: str, history: list[dict], session_id: str = "") -> str:
        set_session_id(session_id)
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        try:
            with trace("Career Chat", group_id=session_id or None):
                while not done:
                    with generation_span(input=messages, model=self.model) as gen_span:
                        response = self.openai.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            tools=tools,
                        )
                        msg = response.choices[0].message
                        if msg.content:
                            gen_span.span_data.output = [{"role": "assistant", "content": msg.content}]
                        if response.usage:
                            gen_span.span_data.usage = {
                                "input_tokens": response.usage.prompt_tokens,
                                "output_tokens": response.usage.completion_tokens,
                            }
                    if response.choices[0].finish_reason == "tool_calls":
                        results = self.handle_tool_call(msg.tool_calls)
                        messages.append(msg)
                        messages.extend(results)
                    else:
                        done = True
            return response.choices[0].message.content

        except openai.RateLimitError:
            push("WARNING: OpenAI rate limit or quota exceeded")
            return (
                "I'm sorry, I'm unable to respond right now due to high demand. "
                "Please try again in a few moments, or reach out directly via "
                "LinkedIn: https://linkedin.com/in/alexrabinovichpro"
            )
        except openai.AuthenticationError:
            push("WARNING: OpenAI authentication error — check API key")
            return (
                "I'm experiencing a technical issue at the moment. "
                "Please connect with me directly on "
                "LinkedIn: https://linkedin.com/in/alexrabinovichpro"
            )
        except openai.APIConnectionError:
            push("WARNING: OpenAI connection error")
            return (
                "I'm having trouble connecting right now. "
                "Please try again shortly, or reach out via "
                "LinkedIn: https://linkedin.com/in/alexrabinovichpro"
            )
        except Exception as e:
            push(f"WARNING: Unexpected error in chat — {type(e).__name__}: {e}")
            print(f"Unexpected chat error: {e}", flush=True)
            return (
                "Something unexpected happened on my end. "
                "Please try again, or get in touch via "
                "LinkedIn: https://linkedin.com/in/alexrabinovichpro"
            )
