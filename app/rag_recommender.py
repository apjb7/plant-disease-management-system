"""
RAG-powered Plant Disease Recommender
=======================================
Replaces the static JSON knowledge base with ChromaDB vector retrieval.
Queries ChromaDB for relevant research chunks based on the detected disease,
builds evidence context, and sends it to the NVIDIA LLM for home gardener guidance.

Output format is IDENTICAL to the original NvidiaLLMRecommender.
"""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class RAGRecommender:
    def __init__(self, chroma_db_path: str = None):
        import chromadb
        from sentence_transformers import SentenceTransformer

        base_dir = Path(__file__).resolve().parent.parent
        if chroma_db_path is None:
            chroma_db_path = str(base_dir / "chroma_db")

        # Load embedding model (same as used during ingestion)
        print("[RAG] Loading sentence-transformers model...")
        self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")

        # Connect to ChromaDB
        print(f"[RAG] Connecting to ChromaDB at {chroma_db_path}")
        self.chroma_client = chromadb.PersistentClient(path=chroma_db_path)
        self.collection = self.chroma_client.get_collection("plant_disease_research")
        print(f"[RAG] Collection loaded: {self.collection.count()} chunks")

        # NVIDIA LLM client
        api_key = os.getenv("NVIDIA_API_KEY")
        base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        model = os.getenv("NVIDIA_MODEL", "openai/gpt-oss-20b")

        if not api_key:
            raise ValueError("NVIDIA_API_KEY is missing in .env")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        print(f"[RAG] NVIDIA LLM model: {self.model}")

    # ─── Disease metadata ──────────────────────────────────────
    DISEASE_INFO = {
        "Mango_Anthracnose": {
            "disease_type": "fungal_disease",
            "causal_agent": "Colletotrichum gloeosporioides",
        },
        "Mango_Powdery_Mildew": {
            "disease_type": "fungal_disease",
            "causal_agent": "Oidium mangiferae",
        },
        "Pepper_Bacterial_Spot": {
            "disease_type": "bacterial_disease",
            "causal_agent": "Xanthomonas spp.",
        },
        "Tomato_Leaf_Mold": {
            "disease_type": "fungal_disease",
            "causal_agent": "Fulvia fulva (syn. Cladosporium fulvum)",
        },
        "Tomato_Early_Blight": {
            "disease_type": "fungal_disease",
            "causal_agent": "Alternaria solani",
        },
        "Tomato_Late_Blight": {
            "disease_type": "oomycete_disease",
            "causal_agent": "Phytophthora infestans",
        },
        "Tomato_Yellow_Leaf_Curl_Virus": {
            "disease_type": "viral_disease",
            "causal_agent": "Tomato Yellow Leaf Curl Virus (TYLCV)",
        },
        "Potato_Early_Blight": {
            "disease_type": "fungal_disease",
            "causal_agent": "Alternaria solani",
        },
        "Potato_Late_Blight": {
            "disease_type": "oomycete_disease",
            "causal_agent": "Phytophthora infestans",
        },
        # Healthy classes
        "Mango_Healthy": {"disease_type": "healthy_leaf", "causal_agent": "None"},
        "Pepper_Healthy": {"disease_type": "healthy_leaf", "causal_agent": "None"},
        "Tomato_Healthy": {"disease_type": "healthy_leaf", "causal_agent": "None"},
        "Potato_Healthy": {"disease_type": "healthy_leaf", "causal_agent": "None"},
    }

    def normalize_class_name(self, class_name: str) -> str:
        if not class_name:
            return class_name
        return class_name.strip().replace(" ", "_").replace("-", "_")

    def retrieve_evidence(self, disease_class: str, severity: str | None = None, n_results: int = 15) -> list[str]:
        """
        Query ChromaDB for research chunks relevant to this disease.
        Uses both semantic search and disease-class metadata filtering.
        """
        # Build a semantic query combining disease name, causal agent, and severity
        info = self.DISEASE_INFO.get(disease_class, {})
        causal_agent = info.get("causal_agent", "")
        disease_type = info.get("disease_type", "")

        # Craft a rich query to maximize retrieval relevance
        query_parts = [
            f"{disease_class.replace('_', ' ')} disease",
            f"management control treatment of {causal_agent}",
        ]
        if severity:
            query_parts.append(f"{severity} severity symptoms management")
        query_parts.append("research findings biological control resistant cultivars integrated management")

        query_text = " ".join(query_parts)

        # Embed the query
        query_embedding = self.embed_model.encode([query_text]).tolist()

        # Query ChromaDB with disease filter
        try:
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                where={"disease_classes": {"$contains": disease_class}},
            )
        except Exception:
            results = None

        documents = results.get("documents", [[]])[0] if results else []
        metadatas = results.get("metadatas", [[]])[0] if results else []

        # Fallback: if no results, try without metadata filter
        if not documents:
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
            )
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]

        # Deduplicate and return
        seen = set()
        unique_chunks = []
        for doc, meta in zip(documents, metadatas):
            doc_hash = hash(doc[:100])
            if doc_hash not in seen:
                seen.add(doc_hash)
                unique_chunks.append(doc)

        return unique_chunks

    def build_research_evidence_from_chunks(self, chunks: list[str], disease_class: str) -> dict:
        """
        Use the LLM to extract structured research evidence from RAG chunks.
        This replaces the static JSON lookup.
        """
        info = self.DISEASE_INFO.get(disease_class, {})

        # Combine chunks into context (limit to ~6000 chars to stay within token limits)
        sanitized_chunks = [self._sanitize_text(c) for c in chunks[:10]]
        context = "\n---\n".join(sanitized_chunks)
        if len(context) > 6000:
            context = context[:6000]

        extraction_prompt = f"""You are a plant pathology expert. You are given research paper excerpts about {disease_class.replace('_', ' ')}.
Disease type: {info.get('disease_type', 'unknown')}
Causal agent: {info.get('causal_agent', 'unknown')}

Extract the following information ONLY from the provided research excerpts. Do not invent any information.
Return valid JSON with these exact fields:

{{
  "pathogen_notes": ["list of 2-3 key facts about the pathogen/disease"],
  "research_findings": ["list of 3-5 key research findings about management, control, or resistance"],
  "supported_actions": ["list of 3-5 evidence-based actions for disease management"],
  "monitoring_points": ["list of 2-3 things to monitor"],
  "cautions": ["list of 2-3 important warnings or limitations"],
  "follow_up": "one sentence about when to reassess or follow up"
}}

Do not wrap the response in markdown code fences. Return only valid JSON.

Research paper excerpts:
{context}"""

        try:
            response = self.client.responses.create(
                model=self.model,
                input=extraction_prompt,
            )
            raw_output = response.output_text.strip()
            cleaned = self._clean_model_output(raw_output)
            parsed = json.loads(cleaned)

            return {
                "pathogen_notes": parsed.get("pathogen_notes", []),
                "research_findings": parsed.get("research_findings", []),
                "supported_actions": parsed.get("supported_actions", []),
                "monitoring_points": parsed.get("monitoring_points", []),
                "cautions": parsed.get("cautions", []),
                "follow_up": parsed.get("follow_up", ""),
                "references_used": ["RAG_ChromaDB_Research_Papers"],
            }
        except Exception as e:
            print(f"[RAG] Evidence extraction error: {e}")
            # Fallback: return raw chunks as findings
            return {
                "pathogen_notes": [f"Detected {info.get('causal_agent', 'pathogen')} infection."],
                "research_findings": chunks[:3] if chunks else ["No research evidence available."],
                "supported_actions": ["Consult local extension services for management recommendations."],
                "monitoring_points": ["Monitor plant for symptom progression."],
                "cautions": ["Always follow label directions when applying any treatments."],
                "follow_up": "Reassess in 7-14 days.",
                "references_used": ["RAG_ChromaDB_Research_Papers"],
            }

    def build_gardener_prompt(self, disease_class: str, severity: str | None, research_evidence: dict) -> str:
        """Build prompt for the home gardener guidance LLM call."""
        info = self.DISEASE_INFO.get(disease_class, {})

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

        prompt.append(f"Predicted class: {disease_class}")
        prompt.append(f"Disease type: {info.get('disease_type', '')}")
        prompt.append(f"Causal agent: {info.get('causal_agent', '')}")

        if severity:
            prompt.append(f"Severity: {severity}")

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
            prompt.append(f"Follow-up rule: {research_evidence['follow_up']}")

        prompt.append("")
        prompt.append("Formatting rules:")
        prompt.append("- summary must be 2 to 3 sentences maximum")
        prompt.append("- what_to_do_now must be a short list")
        prompt.append("- monitoring must be a short list")
        prompt.append("- caution must be a short list")
        prompt.append("- follow_up must be one short sentence")
        prompt.append("- return JSON only")

        return "\n".join(prompt)

    def _clean_model_output(self, output_text: str) -> str:
        cleaned = output_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json"):].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[len("```"):].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        return cleaned

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Replace problematic Unicode characters that crash Windows cp1252 console."""
        replacements = {
            '\u2011': '-',   # non-breaking hyphen
            '\u2010': '-',   # hyphen
            '\u2012': '-',   # figure dash
            '\u2013': '-',   # en dash
            '\u2014': '-',   # em dash
            '\u2018': "'",   # left single quote
            '\u2019': "'",   # right single quote
            '\u201c': '"',   # left double quote
            '\u201d': '"',   # right double quote
            '\u2026': '...', # ellipsis
            '\u00a0': ' ',   # non-breaking space
            '\ufb01': 'fi',  # fi ligature
            '\ufb02': 'fl',  # fl ligature
            '\u2022': '-',   # bullet
            '\u00b7': '-',   # middle dot
        }
        for char, repl in replacements.items():
            text = text.replace(char, repl)
        # Strip any remaining non-ASCII that could cause issues
        text = re.sub(r'[^\x00-\x7F]', ' ', text)
        return text

    def generate(self, predicted_class: str, severity: str | None = None) -> dict:
        """
        Main entry point — identical output format to NvidiaLLMRecommender.generate()
        
        Returns:
            {
                "research_evidence": { pathogen_notes, research_findings, supported_actions,
                                       monitoring_points, cautions, follow_up, references_used },
                "home_gardener_guidance": { summary, what_to_do_now, monitoring, caution, follow_up }
            }
        """
        normalized_class = self.normalize_class_name(predicted_class)
        print(f"[RAG] Generating for: {normalized_class} (severity={severity})")

        # Handle healthy leaves
        info = self.DISEASE_INFO.get(normalized_class, {})
        if info.get("disease_type") == "healthy_leaf":
            return {
                "research_evidence": {
                    "pathogen_notes": ["No disease detected. The plant appears healthy."],
                    "research_findings": ["Healthy leaf tissue shows no signs of pathogen infection."],
                    "supported_actions": ["Continue regular plant care and monitoring."],
                    "monitoring_points": ["Watch for early signs of disease development."],
                    "cautions": [],
                    "follow_up": "Continue routine monitoring.",
                    "references_used": [],
                },
                "home_gardener_guidance": {
                    "summary": "Your plant looks healthy! No signs of disease were detected.",
                    "what_to_do_now": [
                        "Continue your current care routine",
                        "Keep watering and feeding as normal",
                        "Remove any dead or damaged leaves"
                    ],
                    "monitoring": [
                        "Check plants regularly for early signs of disease",
                        "Watch for changes in leaf color or texture"
                    ],
                    "caution": [],
                    "follow_up": "Keep monitoring your plants weekly for best results."
                }
            }

        # Unknown class — no evidence available
        if normalized_class not in self.DISEASE_INFO:
            return self._empty_result()

        # 1. Retrieve relevant research chunks from ChromaDB
        print(f"[RAG] Retrieving evidence from ChromaDB...")
        chunks = self.retrieve_evidence(normalized_class, severity)
        print(f"[RAG] Retrieved {len(chunks)} relevant chunks")

        if not chunks:
            return self._empty_result()

        # 2. Extract structured evidence from chunks (LLM call #1)
        print(f"[RAG] Extracting structured evidence...")
        research_evidence = self.build_research_evidence_from_chunks(chunks, normalized_class)
        print(f"[RAG] Evidence extracted: {len(research_evidence.get('research_findings', []))} findings")

        # 3. Generate home gardener guidance (LLM call #2)
        print(f"[RAG] Generating home gardener guidance...")
        prompt = self.build_gardener_prompt(normalized_class, severity, research_evidence)

        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
            )
            output_text = response.output_text.strip()
            safe_preview = self._sanitize_text(output_text[:200])
            print(f"[RAG] RAW OUTPUT = {safe_preview}...")

            cleaned = self._clean_model_output(output_text)

            try:
                parsed = json.loads(cleaned)
                home_gardener_guidance = {
                    "summary": parsed.get("summary", ""),
                    "what_to_do_now": parsed.get("what_to_do_now", []),
                    "monitoring": parsed.get("monitoring", []),
                    "caution": parsed.get("caution", []),
                    "follow_up": parsed.get("follow_up", ""),
                }
            except json.JSONDecodeError as e:
                print(f"[RAG] JSON parse error: {e}")
                home_gardener_guidance = {
                    "summary": cleaned,
                    "what_to_do_now": [],
                    "monitoring": [],
                    "caution": [],
                    "follow_up": "",
                }
        except Exception as e:
            print(f"[RAG] LLM error: {e}")
            home_gardener_guidance = {
                "summary": "Unable to generate guidance at this time.",
                "what_to_do_now": research_evidence.get("supported_actions", []),
                "monitoring": research_evidence.get("monitoring_points", []),
                "caution": research_evidence.get("cautions", []),
                "follow_up": research_evidence.get("follow_up", ""),
            }

        return {
            "research_evidence": research_evidence,
            "home_gardener_guidance": home_gardener_guidance,
        }

    def _empty_result(self) -> dict:
        return {
            "research_evidence": {
                "pathogen_notes": [],
                "research_findings": [],
                "supported_actions": [],
                "monitoring_points": [],
                "cautions": [],
                "follow_up": "",
                "references_used": [],
            },
            "home_gardener_guidance": {
                "summary": "No recommendation evidence was found for this prediction.",
                "what_to_do_now": [],
                "monitoring": [],
                "caution": [],
                "follow_up": "",
            },
        }
