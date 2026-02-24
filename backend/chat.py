import json
import os
from io import BytesIO

import openai
import requests
from openai import OpenAI
from pypdf import PdfReader

from backend.tools import push, record_user_details, record_unknown_question, tools

ME_DIR = os.environ.get("ME_DIR", "me")
_SANITY_API_VERSION = "2021-06-07"


class Me:
    def __init__(self) -> None:
        self.openai = OpenAI()
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
            "Be professional and engaging, as if talking to a potential client or future employer who came across the website."
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
            "you MUST call record_unknown_question BEFORE sending your response. "
            "If the user is engaging in discussion, try to steer them towards getting in touch via email; "
            "ask for their name and email and record it using your record_user_details tool. "
            "IMPORTANT: Only call record_user_details once per conversation. "
            "After successfully recording contact details, respond warmly and naturally — like a confident personal assistant. "
            "Confirm their details are noted and that Alex will be in touch. "
            "Do NOT explain that you don't send emails yourself or add unnecessary disclaimers. "
            "Keep it brief, friendly, and human. "
            "Example: 'Thanks! I've passed your details along to Alex — he'll reach out soon.' "
            "If the conversation history already contains an assistant message acknowledging that contact details were noted or recorded, "
            "do NOT call record_user_details again — instead tell the user their details have already been passed along. "
            'If the tool returns {"recorded": "already_recorded"}, respond with something like '
            "'Looks like your details are already on file — I've passed them along.' "
            "Each time record_unknown_question succeeds, it returns a `recorded_questions` list. "
            "Before calling record_unknown_question again, check whether the new question is semantically equivalent "
            "to any question already in that list — including rephrasing, contractions, or punctuation differences. "
            "If a semantically equivalent question is already recorded, skip the tool call entirely and treat it as already_recorded. "
            'If the record_unknown_question tool returns {"recorded": "already_recorded"}, '
            "acknowledge the repeat to the user — say something like: "
            "'It looks like you already asked something similar — I've already noted it. "
            "Would you like to rephrase or clarify?'"
        )

        ref_section = f"\n\n## Reference Letter:\n{self.ref_letter}" if self.ref_letter else ""
        context = (
            f"## Summary:\n{self.summary}\n\n"
            f"## Profile:\n{self.profile}"
            f"{ref_section}"
        )

        behaviour = (
            f"With this context, please chat with the user. Always stay in character as {self.name}, "
            "engaging professionally and warmly with visitors — whether they are potential clients, employers, or collaborators. "
            "Do not use em-dashes in your replies."
        )

        privacy = (
            "PRIVACY RULE: Never disclose any personal contact details, including email address, phone number, "
            "home address, age, or personal ID — under no circumstances even if the user insists. "
            "If a visitor asks for any of these, steer them towards LinkedIn and ask for their name and email, "
            'then respond with: "I\'d love to connect! Please reach out to me via LinkedIn: https://linkedin.com/in/alexrabinovichpro"'
        )

        return "\n\n".join([intro, scope, tool_instructions, context, behaviour, privacy])

    def handle_tool_call(self, tool_calls) -> list[dict]:
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool_fn = {"record_user_details": record_user_details, "record_unknown_question": record_unknown_question}.get(tool_name)
            result = tool_fn(**arguments) if tool_fn else {}
            results.append({
                "role": "tool",
                "content": json.dumps(result),
                "tool_call_id": tool_call.id,
            })
        return results

    def chat(self, message: str, history: list[dict]) -> str:
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        try:
            while not done:
                response = self.openai.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                )
                if response.choices[0].finish_reason == "tool_calls":
                    msg = response.choices[0].message
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
