from uuid import uuid4

from sqlalchemy import select

from app.portal.banco import Chamada, Consumo, LimiteGlobal, Usuario, agora, fabrica_sessoes


class CotaExcedida(Exception):
    pass


def reservar(usuario_id: str, trace_id: str, modelo: str, etapa: str,
             input_max: int, output_max: int) -> str:
    if input_max < 0 or output_max < 0:
        raise ValueError("Reserva invalida")
    mes = agora().strftime("%Y-%m")
    with fabrica_sessoes().begin() as sessao:
        global_ = sessao.scalar(select(LimiteGlobal).where(LimiteGlobal.id == 1).with_for_update())
        usuario = sessao.get(Usuario, usuario_id)
        if not global_ or not usuario or not usuario.ativo:
            raise CotaExcedida("Acesso indisponivel.")
        for escopo, limites in (("global", global_), (usuario_id, usuario)):
            consumo = sessao.get(Consumo, (escopo, mes))
            if consumo is None:
                consumo = Consumo(escopo=escopo, mes=mes, input=0, output=0,
                                  reservado_input=0, reservado_output=0)
                sessao.add(consumo)
            if (consumo.input + consumo.reservado_input + input_max > limites.limite_input
                    or consumo.output + consumo.reservado_output + output_max > limites.limite_output):
                raise CotaExcedida("Saldo insuficiente para esta chamada. Consulte suas cotas.")
            consumo.reservado_input += input_max
            consumo.reservado_output += output_max
        chamada_id = uuid4().hex
        sessao.add(Chamada(id=chamada_id, usuario_id=usuario_id, trace_id=trace_id,
                          mes=mes, modelo=modelo, etapa=etapa,
                          reservado_input=input_max, reservado_output=output_max))
    return chamada_id


def finalizar(chamada_id: str, input_real: int | None, output_real: int | None,
              cache: int = 0, duracao_ms: int = 0) -> None:
    with fabrica_sessoes().begin() as sessao:
        sessao.scalar(select(LimiteGlobal).where(LimiteGlobal.id == 1).with_for_update())
        chamada = sessao.get(Chamada, chamada_id)
        if chamada is None or chamada.status != "reservado":
            return
        confirmado = input_real is not None and output_real is not None
        chamada.input = max(0, input_real) if confirmado else chamada.reservado_input
        chamada.output = max(0, output_real) if confirmado else chamada.reservado_output
        chamada.cache = min(max(0, cache), chamada.input)
        chamada.duracao_ms = duracao_ms
        chamada.status = "confirmado" if confirmado else "estimado_erro"
        for escopo in ("global", chamada.usuario_id):
            consumo = sessao.get(Consumo, (escopo, chamada.mes))
            consumo.reservado_input -= chamada.reservado_input
            consumo.reservado_output -= chamada.reservado_output
            consumo.input += chamada.input
            consumo.output += chamada.output