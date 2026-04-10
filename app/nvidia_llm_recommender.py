import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class NvidiaLLMRecommender:
    def __init__(
        self,
        json_path="/Users/adrianpothanah/Plant_Disease_Management_System/Plant-Disease-Management-System/data/final_recommendation_knowledge_base.json"
    ):
        self.json_path = Path(json_path)
        self.knowledge_base = self._load_knowledge_base()

        api_key = os.getenv("NVIDIA_API_KEY")
        base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        model = os.getenv("NVIDIA_MODEL", "openai/gpt-oss-20b")

        if not api_key:
            raise ValueError("NVIDIA_API_KEY is missing in .env")

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model

        print("KNOWLEDGE BASE PATH =", self.json_path.resolve())
        print("TOTAL CLASSES LOADED =", len(self.knowledge_base))
        print("JSON KEYS =", list(self.knowledge_base.keys()))

    def _load_knowledge_base(self):
        if not self.json_path.exists():
            raise FileNotFoundError(f"Knowledge base not found: {self.json_path}")

        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def normalize_class_name(self, class_name: str):
        if not class_name:
            return class_name

        return (
            class_name.strip()
            .replace(" ", "_")
            .replace("-", "_")
        )

    def get_evidence_block(self, predicted_class: str, severity: str | None = None):
        normalized_class = self.normalize_class_name(predicted_class)

        print("ORIGINAL CLASS =", repr(predicted_class))
        print("NORMALIZED CLASS =", repr(normalized_class))
        print("AVAILABLE JSON KEYS =", list(self.knowledge_base.keys()))

        entry = self.knowledge_base.get(normalized_class)

        if not entry:
            return None

        if entry.get("disease_type") == "healthy_leaf":
            return {
                "class_name": normalized_class,
                "disease_type": entry.get("disease_type"),
                "causal_agent": entry.get("causal_agent"),
                "pathogen_notes": entry.get("pathogen_notes", []),
                "evidence_profile": entry.get("evidence_profile", {}),
                "references": entry.get("references", {})
            }

        return {
            "class_name": normalized_class,
            "disease_type": entry.get("disease_type"),
            "causal_agent": entry.get("causal_agent"),
            "pathogen_notes": entry.get("pathogen_notes", []),
            "severity": severity,
            "severity_profile": entry.get("severity_profiles", {}).get(severity, {}),
            "references": entry.get("references", {})
        }

    def _collect_reference_ids(self, *sections):
        refs = []
        for section in sections:
            if not section:
                continue
            for item in section:
                if isinstance(item, dict):
                    refs.extend(item.get("paper_refs", []))
        return sorted(list(set(refs)))

    def build_research_evidence(self, evidence: dict):
        if not evidence:
            return {
                "pathogen_notes": [],
                "research_findings": [],
                "supported_actions": [],
                "monitoring_points": [],
                "cautions": [],
                "follow_up": "",
                "references_used": []
            }

        if evidence.get("disease_type") == "healthy_leaf":
            profile = evidence.get("evidence_profile", {})
        else:
            profile = evidence.get("severity_profile", {})

        pathogen_notes = [item.get("statement", "") for item in evidence.get("pathogen_notes", [])]
        research_findings = [item.get("statement", "") for item in profile.get("research_findings", [])]
        supported_actions = [item.get("action", "") for item in profile.get("supported_actions", [])]
        monitoring_points = [item.get("point", "") for item in profile.get("monitoring_points", [])]
        cautions = [item.get("point", "") for item in profile.get("cautions", [])]
        follow_up = profile.get("follow_up_rule", {}).get("statement", "")

        references_used = self._collect_reference_ids(
            evidence.get("pathogen_notes", []),
            profile.get("research_findings", []),
            profile.get("supported_actions", []),
            profile.get("monitoring_points", []),
            profile.get("cautions", []),
            [profile.get("follow_up_rule", {})]
        )

        return {
            "pathogen_notes": pathogen_notes,
            "research_findings": research_findings,
            "supported_actions": supported_actions,
            "monitoring_points": monitoring_points,
            "cautions": cautions,
            "follow_up": follow_up,
            "references_used": references_used
        }

    def build_prompt(self, evidence: dict, research_evidence: dict):
        class_name = evidence.get("class_name", "")
        disease_type = evidence.get("disease_type", "")
        causal_agent = evidence.get("causal_agent", "")

        prompt = []
        prompt.append("You are a plant disease recommendation assistant for home gardeners.")
        prompt.append("You will receive research-based evidence for one detected plant condition.")
        prompt.append("Your task is to rewrite the evidence into simpler home gardener language.")
        prompt.append("Use only the evidence provided below.")
        prompt.append("Do not invent treatments, chemical doses, timings, or claims.")
        prompt.append("Do not add any information not explicitly supported by the evidence.")
        prompt.append("Do not wrap the JSON in markdown code fences.")
        prompt.append("Write in simple, clear, practical language for non-expert home gardeners.")
        prompt.append("Return only valid JSON with these exact fields:")
        prompt.append("summary, what_to_do_now, monitoring, caution, follow_up")
        prompt.append("")

        prompt.append(f"Predicted class: {class_name}")
        prompt.append(f"Disease type: {disease_type}")
        prompt.append(f"Causal agent: {causal_agent}")

        if evidence.get("severity"):
            prompt.append(f"Severity: {evidence.get('severity')}")

        prompt.append("")
        prompt.append("Research evidence:")
        for item in research_evidence.get("pathogen_notes", []):
            prompt.append(f"Pathogen note: {item}")

        for item in research_evidence.get("research_findings", []):
            prompt.append(f"Research finding: {item}")

        for item in research_evidence.get("supported_actions", []):
            prompt.append(f"Supported action: {item}")

        for item in research_evidence.get("monitoring_points", []):
            prompt.append(f"Monitoring point: {item}")

        for item in research_evidence.get("cautions", []):
            prompt.append(f"Caution: {item}")

        if research_evidence.get("follow_up"):
            prompt.append(f"Follow-up rule: {research_evidence.get('follow_up')}")

        prompt.append("")
        prompt.append("Formatting rules:")
        prompt.append("- summary must be 2 to 3 sentences maximum")
        prompt.append("- what_to_do_now must be a short list")
        prompt.append("- monitoring must be a short list")
        prompt.append("- caution must be a short list")
        prompt.append("- follow_up must be one short sentence")
        prompt.append("- return JSON only")

        return "\n".join(prompt)

    def _clean_model_output(self, output_text: str):
        cleaned_text = output_text.strip()

        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[len("```json"):].strip()
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[len("```"):].strip()

        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3].strip()

        return cleaned_text

    def generate(self, predicted_class: str, severity: str | None = None):
        evidence = self.get_evidence_block(predicted_class, severity)

        if not evidence:
            empty_research = {
                "pathogen_notes": [],
                "research_findings": [],
                "supported_actions": [],
                "monitoring_points": [],
                "cautions": [],
                "follow_up": "",
                "references_used": []
            }
            empty_guidance = {
                "summary": "No recommendation evidence was found for this prediction.",
                "what_to_do_now": [],
                "monitoring": [],
                "caution": [],
                "follow_up": ""
            }
            return {
                "research_evidence": empty_research,
                "home_gardener_guidance": empty_guidance
            }

        research_evidence = self.build_research_evidence(evidence)
        prompt = self.build_prompt(evidence, research_evidence)

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        output_text = response.output_text.strip()
        print("RAW MODEL OUTPUT =", output_text)

        cleaned_text = self._clean_model_output(output_text)
        print("CLEANED MODEL OUTPUT =", cleaned_text)

        try:
            parsed = json.loads(cleaned_text)
            home_gardener_guidance = {
                "summary": parsed.get("summary", ""),
                "what_to_do_now": parsed.get("what_to_do_now", []),
                "monitoring": parsed.get("monitoring", []),
                "caution": parsed.get("caution", []),
                "follow_up": parsed.get("follow_up", "")
            }
        except json.JSONDecodeError as e:
            print("JSON PARSE ERROR =", e)
            home_gardener_guidance = {
                "summary": cleaned_text,
                "what_to_do_now": [],
                "monitoring": [],
                "caution": [],
                "follow_up": ""
            }

        return {
            "research_evidence": research_evidence,
            "home_gardener_guidance": home_gardener_guidance
        }