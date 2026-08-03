import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import Base
from database.models import Document, Template
from services import report_generator


@pytest.mark.asyncio
async def test_generate_section_prompt_contains_selected_document_contents(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session()
    try:
        template = Template(
            name="Prompt Test Template",
            description="Used to verify source document prompt wiring",
            template_type="assessment",
            content="1. REASON FOR REFERRAL\nReferral question: [textarea]",
            is_default=False,
        )
        selected_document = Document(
            filename="selected-source.txt",
            file_path="selected-source.txt",
            file_type="text/plain",
            content="Selected source content reaches the section prompt.",
        )
        unselected_document = Document(
            filename="unselected-source.txt",
            file_path="unselected-source.txt",
            file_type="text/plain",
            content="This content must not be included.",
        )
        db.add_all([template, selected_document, unselected_document])
        db.commit()
        db.refresh(template)
        db.refresh(selected_document)

        captured = {}

        async def capture_prompt(prompt, max_tokens):
            captured["prompt"] = prompt
            captured["max_tokens"] = max_tokens
            return "Generated section"

        monkeypatch.setattr(report_generator, "generate_text", capture_prompt)

        result = await report_generator.generate_report_section(
            db=db,
            template_id=template.id,
            section_name="Reason for Referral",
            document_ids=[selected_document.id],
            section_inputs={"Referral question": "Clarify current needs"},
        )

        assert result == "Generated section"
        assert "--- selected-source.txt ---" in captured["prompt"]
        assert "Selected source content reaches the section prompt." in captured["prompt"]
        assert "unselected-source.txt" not in captured["prompt"]
        assert "This content must not be included." not in captured["prompt"]
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
