from datetime import date, timedelta

import pytest
from playwright.sync_api import Page, expect

APPLICANT = "Тестовый заявитель"
SUCCESS = "Бронирование создано."


@pytest.fixture
def booking_form(page: Page, base_url: str) -> str:
    """Open the form and enter valid baseline data without submitting it."""
    response = page.goto(base_url, wait_until="domcontentloaded")
    assert response is not None and response.ok, "Booking page did not load"
    booking_date = (date.today() + timedelta(days=2)).isoformat()
    page.locator("#room").select_option("small")
    page.locator("#date").fill(booking_date)
    page.locator("#start-time").fill("10:00")
    page.locator("#end-time").fill("10:30")
    page.locator("#participants").fill("4")
    page.locator("#name").fill(APPLICANT)
    page.locator("#email").fill("qa@example.com")
    return booking_date


def test_successful_booking(page: Page, booking_form: str):
    page.get_by_role("button", name="Забронировать").click()

    expect(page.get_by_role("status")).to_have_text(
        f"{SUCCESS} Малая, {booking_form}, 10:00–10:30 · {APPLICANT}",
        use_inner_text=True,
    )


def test_rejects_more_participants_than_room_capacity(page: Page, booking_form: str):
    page.locator("#participants").fill("5")
    page.get_by_role("button", name="Забронировать").click()

    expect(page.locator('[data-error-for="participants"]')).to_be_visible()
    expect(page.locator('[data-error-for="participants"]')).to_contain_text("максимум 4")
    expect(page.get_by_role("status")).to_have_text(
        "Проверьте, пожалуйста, заполнение формы."
    )


@pytest.mark.xfail(
    strict=True,
    reason="BUG-01: форма подтверждает бронь с одинаковым началом и окончанием",
    raises=AssertionError,
)
def test_rejects_equal_start_and_end_times(page: Page, booking_form: str):
    page.locator("#end-time").fill("10:00")
    status = page.get_by_role("status")
    success_message = f"{SUCCESS} Малая, {booking_form}, 10:00–10:00 · {APPLICANT}"
    error_message = "Проверьте, пожалуйста, заполнение формы."
    page.get_by_role("button", name="Забронировать").click()

    observed_status = " ".join(status.inner_text().split())
    if observed_status not in (success_message, error_message):
        pytest.fail(f"Unexpected form status: {observed_status!r}")
    if observed_status == error_message and not page.locator(
        '[data-error-for="endTime"]'
    ).inner_text().strip():
        pytest.fail("Submission was rejected without an error on the end-time field")

    assert observed_status == error_message, f"Zero-duration booking accepted: {observed_status}"
