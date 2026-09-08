# Post‑model moderation – ensure the response conforms to the ConsultaRecarga schema.
# If validation fails, return a safe refusal.

from src.schemas.consulta_recarga import ConsultaRecarga

def moderate_output(data: dict) -> dict:
    """Validate ``data`` against ``ConsultaRecarga``.

    If validation succeeds the original dict (with any extra keys stripped) is
    returned.  On failure a safe refusal dict is produced.
    """
    try:
        model = ConsultaRecarga.model_validate(data)
        return model.model_dump()
    except Exception:
        # Safe refusal – keep the original raw text if present, otherwise a generic message.
        return {
            "intencao": "fora_do_escopo",
            "resposta": data.get("resposta", "Não posso atender a essa solicitação."),
            "confianca": 0.0,
        }
