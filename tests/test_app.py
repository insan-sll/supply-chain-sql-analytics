from streamlit.testing.v1 import AppTest

APP = "../app.py"


def test_overview_renders():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert len(at.metric) == 4


def test_every_question_page_renders():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value("10 business questions").run()
    for i in range(10):
        at.sidebar.selectbox[0].set_value(i).run()
        assert not at.exception, i
        assert at.info, i


def test_playground_runs_and_rejects():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value("SQL playground").run()
    at.button[0].click().run()
    assert not at.exception and at.dataframe
    at.text_area[0].set_value("DROP TABLE orders").run()
    at.button[0].click().run()
    assert at.warning
