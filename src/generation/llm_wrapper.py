"""LLM wrapper for final answer generation (DeepSeek API or local deployment)."""

import logging
from typing import Any

from src.models import DocumentChunk

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a financial analyst assistant. Answer the question using ONLY the provided context. 
If the answer is not in the context, say "Not found in documents". 
Cite the source file after each fact using the format (Source: filename, Page/Sheet: X)."""


def format_context(chunks: list[tuple[DocumentChunk, float]]) -> str:
    parts = []
    for i, (chunk, score) in enumerate(chunks, 1):
        source_info = f"Source: {chunk.source_file}"
        if chunk.metadata.page:
            source_info += f", Page: {chunk.metadata.page}"
        if chunk.metadata.sheet:
            source_info += f", Sheet: {chunk.metadata.sheet}"
        if chunk.metadata.table_name:
            source_info += f", Table: {chunk.metadata.table_name}"
        parts.append(f"[Context {i}] ({source_info})\n{chunk.content}")
    return "\n\n".join(parts)


class LLMWrapper:
    def __init__(self, config: dict[str, Any]):
        self.provider = config.get("provider", "deepseek")
        self.model = config.get("model", "deepseek-chat")
        self.temperature = config.get("temperature", 0.1)
        self.max_tokens = config.get("max_tokens", 500)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.deepseek.com")
        self._client = None

    def generate(self, query: str, context_chunks: list[tuple[DocumentChunk, float]]) -> str:
        context = format_context(context_chunks)

        prompt = f"""Context:
{context}

Question: {query}

Answer:"""

        if self.provider == "deepseek":
            return self._generate_deepseek(prompt)
        if self.provider == "local":
            return self._generate_local(prompt)
        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _generate_deepseek(self, prompt: str) -> str:
        try:
            from openai import OpenAI

            if self._client is None:
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )

            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("DeepSeek generation failed: %s", e)
            return f"Error generating response: {e}"

    def _generate_local(self, prompt: str) -> str:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            if self._client is None:
                logger.info("Loading local model: %s", self.model)
                tokenizer = AutoTokenizer.from_pretrained(self.model, trust_remote_code=True)
                model = AutoModelForCausalLM.from_pretrained(
                    self.model,
                    trust_remote_code=True,
                    torch_dtype=torch.float16,
                    device_map="auto",
                )
                self._client = (tokenizer, model)

            tokenizer, model = self._client
            full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
            inputs = tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=4096)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=self.max_tokens,
                    temperature=self.temperature,
                    do_sample=self.temperature > 0,
                )

            response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            return response.strip()
        except Exception as e:
            logger.error("Local LLM generation failed: %s", e)
            return f"Error generating response: {e}"
