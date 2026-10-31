"""Travel booking record tests.

Traces to: UNION-SPEC Core function 4 (Travel booking records — air or
hotel, date range, amount in cents, recorded -> confirmed / cancelled
lifecycle; records of reservations made elsewhere, the build books
nothing) and Core function 1/2 (the program/traveler substrate);
Implementation contract for ``finance/store.py`` booking methods;
control family SI-10 (integer cents, validation before mutation).
"""

import unittest

from finance_helpers import (
    MEMBER,
    OUTSIDER,
    VIEWER,
    make_booking,
    make_employee,
    make_store,
    make_traveler,
)
from finance.errors import NotFoundError, PermissionDenied, ValidationError

BOOKING_KEYS = {
    "id", "program_id", "participant_id", "kind", "start_date",
    "end_date", "amount_cents", "status", "created_by", "created_utc",
}


class BookingBase(unittest.TestCase):
    """A canonical program with one traveler and one employee."""

    def setUp(self):
        self.store, self.audit, self.program_id = make_store()
        self.traveler = make_traveler(self.store, self.program_id)
        self.employee = make_employee(self.store, self.program_id)
        self.trav_id = self.traveler["id"]
        self.emp_id = self.employee["id"]


class TestCreateBooking(BookingBase):
    """Core 4: Travel booking records — creation shape/validation."""

    def test_create_booking_returns_the_contract_dict(self):
        """Core 4: Travel booking records. Contract: create_booking
        returns {id, program_id, participant_id, kind, start_date,
        end_date, amount_cents, status, created_by, created_utc} with
        the bkg- prefix and initial status recorded."""
        booking = make_booking(self.store, self.program_id, self.trav_id)
        self.assertEqual(set(booking.keys()), BOOKING_KEYS)
        self.assertEqual(booking["id"], "bkg-1")
        self.assertEqual(booking["program_id"], self.program_id)
        self.assertEqual(booking["participant_id"], self.trav_id)
        self.assertEqual(booking["kind"], "air")
        self.assertEqual(booking["start_date"], "2026-01-10")
        self.assertEqual(booking["end_date"], "2026-01-12")
        self.assertEqual(booking["amount_cents"], 30000)
        self.assertEqual(booking["status"], "recorded")
        self.assertEqual(booking["created_by"], "bob")

    def test_hotel_kind_is_accepted(self):
        """Core 4: Travel booking records. Contract: kind must be air
        or hotel — hotel is valid."""
        booking = make_booking(self.store, self.program_id, self.trav_id,
                               kind="hotel")
        self.assertEqual(booking["kind"], "hotel")

    def test_booking_ids_are_sequential(self):
        """Core 4: Travel booking records. Contract: ids are
        sequential per object type with the bkg- prefix."""
        first = make_booking(self.store, self.program_id, self.trav_id)
        second = make_booking(self.store, self.program_id, self.trav_id,
                              kind="hotel")
        self.assertEqual([first["id"], second["id"]], ["bkg-1", "bkg-2"])

    def test_bad_kind_is_a_validation_error(self):
        """Core 4: Travel booking records. Contract: kind must be air
        or hotel."""
        for bad in ("train", "car", "Air", "", None):
            with self.subTest(kind=bad):
                with self.assertRaises(ValidationError):
                    make_booking(self.store, self.program_id, self.trav_id,
                                 kind=bad)
        self.assertEqual(self.store.list_bookings(self.program_id, MEMBER),
                         [])

    def test_booking_for_employee_is_a_validation_error(self):
        """Core 4: Travel booking records. Contract: the participant
        must be a traveler (an employee participant ->
        ValidationError)."""
        with self.assertRaises(ValidationError):
            make_booking(self.store, self.program_id, self.emp_id)

    def test_booking_for_unknown_participant_is_not_found(self):
        """Core 4: Travel booking records. Contract: the participant
        must exist in this program (NotFoundError)."""
        with self.assertRaises(NotFoundError):
            make_booking(self.store, self.program_id, "part-999999")

    def test_end_before_start_is_a_validation_error(self):
        """Core 4: Travel booking records. Contract: 'end_date not
        before start_date' — an end one day before the start is
        rejected and nothing is stored."""
        with self.assertRaises(ValidationError):
            make_booking(self.store, self.program_id, self.trav_id,
                         start_date="2026-01-12", end_date="2026-01-11")
        self.assertEqual(self.store.list_bookings(self.program_id, MEMBER),
                         [])

    def test_same_day_start_and_end_is_ok(self):
        """Core 4: Travel booking records. end_date == start_date does
        not violate 'not before'."""
        booking = make_booking(self.store, self.program_id, self.trav_id,
                               start_date="2026-01-10",
                               end_date="2026-01-10")
        self.assertEqual(booking["start_date"], booking["end_date"])

    def test_bad_dates_are_validation_errors(self):
        """Core 4: Travel booking records. Contract: both dates must
        be valid ISO calendar dates."""
        for start, end in (("2026-13-10", "2026-01-12"),
                           ("2026-01-10", "2026-02-30"),
                           ("Jan 10 2026", "2026-01-12"),
                           ("2026-01-10", "")):
            with self.subTest(start=start, end=end):
                with self.assertRaises(ValidationError):
                    make_booking(self.store, self.program_id, self.trav_id,
                                 start_date=start, end_date=end)

    def test_float_or_negative_amount_is_a_validation_error(self):
        """Core 4: Travel booking records (SI-10). amount_cents must
        be an int >= 0: floats (even integral), bools and negatives
        are rejected."""
        for bad in (100.0, 99.9, True, -1):
            with self.subTest(amount=bad):
                with self.assertRaises(ValidationError):
                    make_booking(self.store, self.program_id, self.trav_id,
                                 amount_cents=bad)

    def test_zero_amount_is_ok(self):
        """Core 4: Travel booking records. amount_cents is an int >= 0,
        so a zero-amount booking record is valid."""
        booking = make_booking(self.store, self.program_id, self.trav_id,
                               amount_cents=0)
        self.assertEqual(booking["amount_cents"], 0)

    def test_failed_booking_consumes_no_id(self):
        """Core 4: Travel booking records (SI-10). A failed creation
        changes nothing: the next successful booking is bkg-1."""
        with self.assertRaises(ValidationError):
            make_booking(self.store, self.program_id, self.trav_id,
                         kind="train")
        booking = make_booking(self.store, self.program_id, self.trav_id)
        self.assertEqual(booking["id"], "bkg-1")

    def test_non_member_create_is_denied(self):
        """Core 4: Travel booking records (AC-3). A non-member cannot
        create a booking (membership boundary)."""
        with self.assertRaises(PermissionDenied):
            self.store.create_booking(
                self.program_id, self.trav_id, "air", "2026-01-10",
                "2026-01-12", 30000, OUTSIDER,
            )

    def test_get_booking_roundtrip_and_cross_program_not_found(self):
        """Core 4: Travel booking records. get_booking returns the
        record; an id from another program raises NotFoundError."""
        booking = make_booking(self.store, self.program_id, self.trav_id)
        got = self.store.get_booking(self.program_id, booking["id"], VIEWER)
        self.assertEqual(got["id"], booking["id"])
        self.assertEqual(set(got.keys()), BOOKING_KEYS)
        other = self.store.create_program("other-program", MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.get_booking(other["id"], booking["id"], MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.get_booking(self.program_id, "bkg-999999", MEMBER)


class TestBookingLifecycle(BookingBase):
    """Core 4: Travel booking records — recorded/confirmed/cancelled."""

    def test_recorded_to_confirmed_to_cancelled(self):
        """Core 4: Travel booking records. The lifecycle: recorded ->
        confirmed (confirm_booking, action ``record``) -> cancelled
        (cancel_booking, action ``enter``)."""
        booking = make_booking(self.store, self.program_id, self.trav_id)
        confirmed = self.store.confirm_booking(
            self.program_id, booking["id"], MEMBER
        )
        self.assertEqual(confirmed["status"], "confirmed")
        self.assertEqual(set(confirmed.keys()), BOOKING_KEYS)
        cancelled = self.store.cancel_booking(
            self.program_id, booking["id"], MEMBER
        )
        self.assertEqual(cancelled["status"], "cancelled")

    def test_cancel_directly_from_recorded(self):
        """Core 4: Travel booking records. Contract: cancel is allowed
        from recorded as well as confirmed."""
        booking = make_booking(self.store, self.program_id, self.trav_id)
        cancelled = self.store.cancel_booking(
            self.program_id, booking["id"], MEMBER
        )
        self.assertEqual(cancelled["status"], "cancelled")

    def test_confirm_of_confirmed_is_a_validation_error(self):
        """Core 4: Travel booking records. Contract: confirm requires
        status recorded (else ValidationError)."""
        booking = make_booking(self.store, self.program_id, self.trav_id)
        self.store.confirm_booking(self.program_id, booking["id"], MEMBER)
        with self.assertRaises(ValidationError):
            self.store.confirm_booking(self.program_id, booking["id"], MEMBER)

    def test_confirm_of_cancelled_is_a_validation_error(self):
        """Core 4: Travel booking records. A cancelled booking cannot
        be confirmed (ValidationError) and stays cancelled."""
        booking = make_booking(self.store, self.program_id, self.trav_id)
        self.store.cancel_booking(self.program_id, booking["id"], MEMBER)
        with self.assertRaises(ValidationError):
            self.store.confirm_booking(self.program_id, booking["id"], MEMBER)
        got = self.store.get_booking(self.program_id, booking["id"], MEMBER)
        self.assertEqual(got["status"], "cancelled")

    def test_cancel_of_cancelled_is_a_validation_error(self):
        """Core 4: Travel booking records. Contract: cancel requires
        status recorded or confirmed — cancelling a cancelled booking
        raises ValidationError."""
        booking = make_booking(self.store, self.program_id, self.trav_id)
        self.store.cancel_booking(self.program_id, booking["id"], MEMBER)
        with self.assertRaises(ValidationError):
            self.store.cancel_booking(self.program_id, booking["id"], MEMBER)


class TestListBookings(BookingBase):
    """Core 4: Travel booking records — list filters."""

    def setUp(self):
        super().setUp()
        self.air = make_booking(self.store, self.program_id, self.trav_id,
                                kind="air", amount_cents=30000)
        self.hotel = make_booking(self.store, self.program_id, self.trav_id,
                                  kind="hotel", amount_cents=25000)
        self.store.confirm_booking(self.program_id, self.hotel["id"], MEMBER)
        self.cancelled = make_booking(self.store, self.program_id,
                                      self.trav_id, kind="air",
                                      amount_cents=12000)
        self.store.cancel_booking(self.program_id, self.cancelled["id"],
                                  MEMBER)

    def test_list_bookings_in_creation_order(self):
        """Core 4: Travel booking records. Contract: list_bookings
        returns bookings in creation order."""
        bookings = self.store.list_bookings(self.program_id, MEMBER)
        self.assertEqual(
            [b["id"] for b in bookings],
            [self.air["id"], self.hotel["id"], self.cancelled["id"]],
        )

    def test_list_bookings_status_filter(self):
        """Core 4: Travel booking records. Contract: list_bookings
        honours status= over recorded/confirmed/cancelled."""
        recorded = self.store.list_bookings(self.program_id, MEMBER,
                                            status="recorded")
        self.assertEqual([b["id"] for b in recorded], [self.air["id"]])
        confirmed = self.store.list_bookings(self.program_id, MEMBER,
                                             status="confirmed")
        self.assertEqual([b["id"] for b in confirmed], [self.hotel["id"]])
        cancelled = self.store.list_bookings(self.program_id, MEMBER,
                                             status="cancelled")
        self.assertEqual([b["id"] for b in cancelled], [self.cancelled["id"]])

    def test_list_bookings_kind_filter(self):
        """Core 4: Travel booking records. Contract: list_bookings
        honours kind= over air/hotel."""
        air = self.store.list_bookings(self.program_id, MEMBER, kind="air")
        self.assertEqual(
            [b["id"] for b in air], [self.air["id"], self.cancelled["id"]]
        )
        hotel = self.store.list_bookings(self.program_id, MEMBER, kind="hotel")
        self.assertEqual([b["id"] for b in hotel], [self.hotel["id"]])

    def test_list_bookings_combined_filters(self):
        """Core 4: Travel booking records. status= and kind= combine."""
        result = self.store.list_bookings(self.program_id, MEMBER,
                                          status="cancelled", kind="air")
        self.assertEqual([b["id"] for b in result], [self.cancelled["id"]])
        result = self.store.list_bookings(self.program_id, MEMBER,
                                          status="cancelled", kind="hotel")
        self.assertEqual(result, [])

    def test_list_bookings_unknown_filter_values_are_validation_errors(self):
        """Core 4: Travel booking records. Contract: 'unknown filter
        values -> ValidationError' for both status and kind."""
        with self.assertRaises(ValidationError):
            self.store.list_bookings(self.program_id, MEMBER, status="pending")
        with self.assertRaises(ValidationError):
            self.store.list_bookings(self.program_id, MEMBER, kind="train")


if __name__ == "__main__":
    unittest.main()
