"""Core function 9: payroll run records (SI-10).

A run record carries a caller-recorded gross amount in integer
cents. This substrate performs no pay calculation, no job costing,
and no disbursement -- those engines are Extended, and the record
shape carries no computed field for them to hide in.
"""

import unittest

from erp.errors import NotFoundError, ValidationError

from erp_helpers import (OPERATOR, PERSON_REF, make_org, make_person,
                         make_store)


class PayrollRunTests(unittest.TestCase):
    def setUp(self):
        self.store, _ = make_store()
        self.org = make_org(self.store)
        make_person(self.store, self.org)

    def test_run_records_caller_amount(self):
        run = self.store.create_payroll_run(
            OPERATOR, self.org["id"], PERSON_REF, "RUN-2024-03",
            "March 2024 (label)", 485000)
        self.assertEqual(run["gross_cents"], 485000)
        self.assertEqual(
            set(run.keys()),
            {"id", "org_id", "person_ref", "run_ref", "period_label",
             "gross_cents", "created_by", "created_utc"})

    def test_amount_types_rejected(self):
        for bad in (100.0, True, "485000", -1):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.create_payroll_run(
                    OPERATOR, self.org["id"], PERSON_REF, "RUN-X",
                    "Period (label)", bad)

    def test_run_ref_unique_and_person_required(self):
        self.store.create_payroll_run(
            OPERATOR, self.org["id"], PERSON_REF, "RUN-1",
            "Period (label)", 100)
        with self.assertRaises(ValidationError):
            self.store.create_payroll_run(
                OPERATOR, self.org["id"], PERSON_REF, "RUN-1",
                "Period (label)", 100)
        with self.assertRaises(NotFoundError):
            self.store.create_payroll_run(
                OPERATOR, self.org["id"], "PERSON-404", "RUN-2",
                "Period (label)", 100)


if __name__ == "__main__":
    unittest.main()
