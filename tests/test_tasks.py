from sqlmodel import Session, select
from app.tasks import process_emails_task_logic
from app.models.category import Category
from app.models.email import Email

def test_process_emails_logic(session: Session, mocker):

    owner_email = "test@example.com"
    user_info = {"email": owner_email}
    token_data = {"access_token": "fake_token"}
    
    cat1 = Category(name="Jobs", description="Job offers", user_email=owner_email)
    cat2 = Category(name="Promotions", description="Marketing emails", user_email=owner_email)
    session.add(cat1)
    session.add(cat2)
    session.commit()

    mock_list_messages = mocker.patch("app.tasks.list_messages", return_value=[{"id": "msg1"}])
    mock_get_details = mocker.patch("app.tasks.get_message_details", return_value={
        "id": "msg1",
        "snippet": "Job opportunity...",
        "body": "<html>...</html>",
        "date": "Some Date",
        "from": "recruiter@company.com"
    })
    mock_archive_email = mocker.patch("app.tasks.archive_email")

    mock_ai_result = {"summary": "A great job offer", "category": "Jobs"}
    mock_summarize = mocker.patch("app.tasks.summarize_and_categorize_email", return_value=mock_ai_result)
    
    mocker.patch("app.tasks.get_gmail_service")

    process_emails_task_logic(owner_email, user_info, token_data, db_session=session)

    mock_list_messages.assert_called_once()
    mock_get_details.assert_called_with(mocker.ANY, "msg1")
    mock_summarize.assert_called_once()
    mock_archive_email.assert_called_with(mocker.ANY, "msg1")

    processed_email = session.exec(select(Email).where(Email.id == "msg1")).one_or_none()
    assert processed_email is not None
    assert processed_email.id == "msg1"
    assert processed_email.summary == "A great job offer"
    assert processed_email.category_id == cat1.id
    assert processed_email.user_email == owner_email