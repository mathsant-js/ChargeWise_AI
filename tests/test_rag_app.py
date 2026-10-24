from streamlit.testing.v1 import AppTest
from app.app import operational_error


def test_streamlit_form_starts_and_rejects_blank_question():
    app = AppTest.from_file("app/app.py", default_timeout=20).run()
    assert not app.exception
    assert app.title[0].value == "ChargeWise AI"
    app.button[0].click().run()
    assert not app.exception
    assert any("Digite uma pergunta" in warning.value for warning in app.warning)


def test_operational_error_distinguishes_index_from_model():
    assert "Índice não encontrado" in operational_error(
        RuntimeError("Collection chargewise_knowledge does not exist"))
    assert "Modelo Ollama indisponível" in operational_error(
        RuntimeError("model qwen does not exist"))
