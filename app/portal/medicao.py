import json
from contextvars import ContextVar
from dataclasses import dataclass
from time import perf_counter

from langchain_openai import ChatOpenAI

from app.portal.cotas import finalizar, reservar


@dataclass
class ContextoConsumo:
    usuario_id: str
    trace_id: str


contexto_consumo: ContextVar[ContextoConsumo | None] = ContextVar("consumo", default=None)


class ModeloMedido(ChatOpenAI):
    etapa_consumo: str = "geracao"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        contexto = contexto_consumo.get()
        if contexto is None:
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        # Bytes UTF-8 superestimam tokens; a margem cobre o envelope e schemas internos.
        entrada_max = len(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")) + 4096
        saida_max = int(payload.get("max_tokens") or self.max_tokens or 1024)
        chamada_id = reservar(contexto.usuario_id, contexto.trace_id, self.model_name,
                              self.etapa_consumo, entrada_max, saida_max)
        inicio = perf_counter()
        try:
            resultado = super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except Exception:
            finalizar(chamada_id, None, None, duracao_ms=int((perf_counter() - inicio) * 1000))
            raise
        uso = (resultado.llm_output or {}).get("token_usage", {})
        finalizar(chamada_id, uso.get("prompt_tokens"), uso.get("completion_tokens"),
                  cache=(uso.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
                  duracao_ms=int((perf_counter() - inicio) * 1000))
        return resultado