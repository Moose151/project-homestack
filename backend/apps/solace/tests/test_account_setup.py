"""Regression coverage for the account-first setup and payment projections."""
from datetime import date
from unittest.mock import patch

from django.urls import reverse
from django.test import TestCase

from apps.accounts.models import User
from apps.core.models import get_active_household, Household
from apps.solace.account_schedule import describe_schedule
from apps.solace.models import AccountTransfer, Bill, BillOccurrence, SolaceSettings, Payday, BudgetBucket
from apps.solace.selectors import bill_display_projection
from apps.solace.data_tools import export_sheets
from apps.solace.tests import test_forecast as helpers
from apps.solace.tests.test_solace import _make_user, _login, _reauth


class AccountProjectionTests(TestCase):
    setUp = helpers.BillsAccountForecastTests.setUp
    at = helpers.BillsAccountForecastTests.at
    bill = helpers.BillsAccountForecastTests.bill
    balance = helpers.BillsAccountForecastTests.balance
    forecast = helpers.BillsAccountForecastTests.forecast

    def test_ended_mortgage_is_flagged_without_rewriting_history(self):
        self.balance()
        bill = self.bill(due_at=self.at(1), recurrence_rule="FREQ=WEEKLY;INTERVAL=2", end_date=date(2028, 8, 1))
        forecast = self.forecast()
        self.assertTrue(forecast['needs_review'])
        self.assertIsNone(forecast['safe_to_withdraw'])
        self.assertEqual(forecast['schedule_issues'][0]['bill_id'], bill.id)
        bill.refresh_from_db()
        self.assertEqual(bill.end_date, date(2028, 8, 1))
        bill.end_date = None
        bill.save()
        forecast = self.forecast()
        self.assertFalse(forecast['needs_review'])
        self.assertEqual(forecast['total_bills'], '1200.00')

    def test_end_on_first_payment_is_explained_before_saving(self):
        bill = self.bill(recurrence_rule='FREQ=WEEKLY;INTERVAL=2', end_date=date(2028, 8, 10))
        schedule = describe_schedule(bill, as_of=self.as_of)
        self.assertEqual(schedule['status'], 'Stops after first payment')
        self.assertEqual(len(schedule['next_dates']), 1)

    def test_automatic_payments_in_snapshot_are_not_carried_as_debt(self):
        self.balance()
        bill = self.bill(due_at=self.at(1), recurrence_rule='FREQ=WEEKLY;INTERVAL=2', is_autopay=True)
        BillOccurrence.objects.create(household=self.household, bill=bill, due_at=bill.due_at, amount=bill.amount)
        forecast = self.forecast()
        self.assertEqual(forecast['total_bills'], '1200.00')
        self.assertEqual(forecast['overdue_total'], '0.00')
        self.assertEqual(forecast['timeline'][0]['date'], '2028-08-15')
        self.assertEqual(forecast['timeline'][0]['items'][0]['status'], 'automatic')
        self.assertEqual(BillOccurrence.objects.get(bill=bill, due_at=bill.due_at).status, 'upcoming')

    def test_scheduled_transfers_use_local_dates_and_replace_payday_allocations(self):
        self.balance()
        SolaceSettings.objects.create(household=self.household, forecast_funding_source='transfers')
        AccountTransfer.objects.create(household=self.household, name='Bank transfer', amount='700', due_at=self.at(3), recurrence_rule='FREQ=WEEKLY;INTERVAL=2', end_date=date(2028, 8, 17))
        AccountTransfer.objects.create(household=self.household, name='Paused', amount='999', due_at=self.at(3), is_active=False)
        Payday.objects.create(household=self.household, title='Full salary', expected_amount='4000', pay_at=self.at(3))
        BudgetBucket.objects.create(household=self.household, name='Bills', purpose='bills', allocation_method='percentage', allocation_value=50)
        forecast = self.forecast()
        self.assertEqual(forecast['total_contributions'], '1400.00')
        self.assertEqual([row['date'] for row in forecast['timeline']], ['2028-08-03', '2028-08-17'])
        SolaceSettings.objects.update(forecast_funding_source='pay_plan')
        self.assertEqual(self.forecast()['total_contributions'], '2000.00')

    def test_private_transfers_do_not_leak_into_forecast(self):
        SolaceSettings.objects.create(household=self.household, forecast_funding_source='transfers')
        other = User.objects.create_user(username='private-owner', display_name='Owner', role=User.Role.ADMIN)
        AccountTransfer.objects.create(household=self.household, name='Hidden transfer', amount='999', due_at=self.at(3), visibility='private', created_by=other)
        self.user.role = User.Role.USER
        self.assertEqual(self.forecast()['total_contributions'], '0.00')

    def test_home_payment_projection_uses_next_payment_and_respects_pause(self):
        bill = self.bill(due_at=self.at(1), recurrence_rule='FREQ=WEEKLY;INTERVAL=2', is_autopay=True)
        with patch('apps.solace.selectors.timezone.localdate', return_value=self.as_of):
            projection = bill_display_projection(self.user, {bill.id})[bill.id]
        self.assertTrue(projection['next_payment_at'].startswith('2028-08-15'))
        bill.is_active = False
        bill.save()
        self.assertIsNone(bill_display_projection(self.user, {bill.id})[bill.id]['next_payment_at'])


class AccountSetupApiTests(TestCase):
    def setUp(self):
        self.user = _make_user('setup-admin')
        self.household = get_active_household()
        self.household.timezone = 'Australia/Brisbane'
        self.household.save()
        self.url = reverse('solace-transfer-list')
        self.data = {'name': 'Fortnightly transfer', 'amount': '2700.00', 'due_at': '2028-08-03T00:00:00+10:00', 'recurrence_rule': 'FREQ=WEEKLY;INTERVAL=2'}

    def login(self):
        _login(self.client, self.user.username)
        _reauth(self.client)

    def test_sensitive_endpoints_require_unlock_and_node_access(self):
        _login(self.client, self.user.username)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(reverse('solace-bill-preview'), {'name': 'Bill'}, content_type='application/json').status_code, 403)
        _make_user('no-money', User.Role.MANAGER)
        _login(self.client, 'no-money'); _reauth(self.client)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_transfer_create_edit_and_pause_preserve_amount_and_scope(self):
        self.login()
        response = self.client.post(self.url, self.data, content_type='application/json')
        self.assertEqual(response.status_code, 201, response.content)
        transfer = AccountTransfer.objects.get(pk=response.json()['id'])
        self.assertEqual(transfer.household, self.household)
        self.assertEqual(transfer.created_by, self.user)
        url = reverse('solace-transfer-detail', args=[transfer.pk])
        response = self.client.patch(url, {'is_active': False}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['amount'], '2700.00')
        self.assertFalse(response.json()['is_active'])
        foreign = Household.objects.create(name='Elsewhere', slug='elsewhere')
        hidden = AccountTransfer.all_objects.create(household=foreign, **{**self.data, 'due_at': transfer.due_at})
        self.assertEqual(self.client.patch(reverse('solace-transfer-detail', args=[hidden.pk]), {'amount': '1'}, content_type='application/json').status_code, 404)
        self.assertEqual(len(self.client.get(self.url).json()), 1)

    def test_invalid_transfer_cannot_save(self):
        self.login()
        for change in [{'amount': '0'}, {'amount': '-10'}, {'end_date': '2028-08-01'}, {'recurrence_rule': 'FREQ=WEEKLY;INTERVAL=0'}, {'name': ' '}]:
            with self.subTest(change=change):
                response = self.client.post(self.url, {**self.data, **change}, content_type='application/json')
                self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(AccountTransfer.objects.exists())

    def test_readable_backup_includes_account_transfers(self):
        self.login()
        self.client.post(self.url, self.data, content_type='application/json')
        sheets = dict(export_sheets(self.user))
        self.assertEqual(sheets['Account Transfers'][0]['name'], 'Fortnightly transfer')
        self.assertEqual(sheets['Account Transfers'][0]['amount'], '2700.00')

    def test_preview_does_not_create_bill_or_occurrences(self):
        self.login()
        response = self.client.post(reverse('solace-bill-preview'), {**self.data, 'end_date': '2028-08-03'}, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['status'], 'Stops after first payment')
        self.assertFalse(Bill.objects.exists())
        self.assertFalse(BillOccurrence.objects.exists())
        response = self.client.post(reverse('solace-bill-preview'), {**self.data, 'recurrence_rule': 'FREQ=WEEKLY;INTERVAL=banana'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
