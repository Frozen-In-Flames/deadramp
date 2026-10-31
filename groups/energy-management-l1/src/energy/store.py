"""Energy store: customer and provider registries, reverse-auction
and bid records, price observations, alert subscriptions and alert
records, and advisory engagement records.

Clean-room implementation of the union spec's implementation
contract.

Role permission is enforced on every operation when the actor is a
User-like object: the action named for the operation must be in the
actor's role permission set (see :mod:`energy.access`). A plain
string actor carries identity (for provenance) but no role, so role
enforcement for those happens in the service layer (the sibling
builds' convention).

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``cust-``,
``prov-``, ``auc-``, ``bid-``, ``obs-``, ``sub-``, ``alrt-``,
``eng-``).

Derivation discipline: any status that depends on a date is derived
at read time and never stored. An auction's status
(``upcoming`` / ``open`` / ``closed``) is computed from its window
and any recorded early close against the read clock, and the
auction **outcome** -- the winning bid -- is computed on read from
the bid records alone by the single seam :func:`_derive_winner`.
The stored auction record carries no status key and no outcome
key. Event-driven state, by contrast, is stored, as in the sibling
builds' record lifecycles: an engagement's ``open`` / ``closed``
state, a subscription's active flag, and an auction's recorded
early close change only through recorded actions.

Price discipline: prices are integer cents per the auction's (or
series') stated unit. Any price that is not a Python ``int``
(booleans and floats included, even integral floats) raises
:class:`ValidationError`. No payment, settlement, or billing
function exists here; a winning bid is a record selection, and
paying on it is Extended.

Scoring discipline: the outcome derivation selects the lowest
recorded bid -- a minimum over recorded values. Nothing in this
store computes a score, a rating, or a ranking of any customer or
provider, no record shape carries a field for one, and the outcome
view deliberately returns the single winning selection plus
counts, never a provider leaderboard.

Privacy discipline: customers and providers are known only by a
caller-supplied opaque ``ref`` and a label. No entity shape has a
field that can hold a real name, address, email, phone number, or
account identifier. This store also controls nothing physical: it
holds records about energy procurement and operates no grid,
charging, building, or metering system.

The store records every successful mutation to its audit log (when
one is attached). Reads are not audited here; denied attempts and
audit reads are the HTTP layer's responsibility, so nothing is
recorded twice.
"""

import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, ValidationError

NOTIFICATION_KINDS = ("price_change", "contract_change", "market_update")
ENGAGEMENT_KINDS = ("budgeting", "market_intelligence", "risk_management")
ENGAGEMENT_STATUSES = ("open", "closed")
AUCTION_STATUSES = ("upcoming", "open", "closed")


def _utc_now():
    return datetime.now(timezone.utc)


def _parse_moment(value, field):
    """Parse an ISO date or datetime into an aware datetime."""
    if isinstance(value, datetime):
        moment = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                moment = datetime.strptime(text, "%Y-%m-%d")
            else:
                moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError("%s is not an ISO date or datetime: %r" % (field, value))
    else:
        raise ValidationError("%s must be an ISO date or datetime string" % field)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _price(value, field, allow_zero=False):
    """Validate an integer-cents price; floats and bools are rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % field)
    if allow_zero and value < 0:
        raise ValidationError("%s must not be negative" % field)
    if not allow_zero and value <= 0:
        raise ValidationError("%s must be positive" % field)
    return value


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _optional_text(value, field):
    if value is None:
        return None
    return _text(value, field)


def _derive_winner(bids):
    """Outcome derivation seam: the winning bid of a reverse auction
    is the lowest-priced bid; ties are broken by earliest sequence.

    Pure function over the bid record list. Returns the winning bid
    record, or None when there are no bids. This selection is a
    minimum over recorded values -- it is the auction's own outcome,
    not a score or rating of any provider.
    """
    if not bids:
        return None
    return min(bids, key=lambda b: (b["price_cents_per_unit"], b["seq"]))


class EnergyStore:
    """In-memory energy-procurement records store with an optional
    audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._customers = {}
        self._providers = {}
        self._auctions = {}
        self._bids = {}
        self._observations = {}
        self._subscriptions = {}
        self._alerts = {}
        self._engagements = {}
        self._counters = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _record(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    @staticmethod
    def _check_role(actor, action):
        if hasattr(actor, "role"):
            require(actor, action)

    def _customer(self, customer_id):
        customer = self._customers.get(customer_id)
        if customer is None:
            raise NotFoundError("no such customer: %r" % (customer_id,))
        return customer

    def _provider(self, provider_id):
        provider = self._providers.get(provider_id)
        if provider is None:
            raise NotFoundError("no such provider: %r" % (provider_id,))
        return provider

    def _auction(self, auction_id):
        auction = self._auctions.get(auction_id)
        if auction is None:
            raise NotFoundError("no such auction: %r" % (auction_id,))
        return auction

    # -- registries ---------------------------------------------------------

    def _create_party(self, actor, table, prefix, kind, ref, label):
        self._check_role(actor, "register")
        _text(ref, "ref")
        _text(label, "label")
        with self._lock:
            for existing in table.values():
                if existing["ref"] == ref:
                    raise ValidationError("%s ref already exists: %r" % (kind, ref))
            party = {
                "id": self._mint(prefix),
                "ref": ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            table[party["id"]] = party
        self._record(actor, "%s_create" % kind, party["id"], {"ref": ref})
        return dict(party)

    def create_customer(self, actor, ref, label):
        """Register a customer by opaque reference."""
        return self._create_party(actor, self._customers, "cust-",
                                  "customer", ref, label)

    def get_customer(self, actor, customer_id):
        self._check_role(actor, "read")
        return dict(self._customer(customer_id))

    def list_customers(self, actor):
        self._check_role(actor, "read")
        return [dict(c) for c in self._customers.values()]

    def create_provider(self, actor, ref, label):
        """Register an energy provider by opaque reference."""
        return self._create_party(actor, self._providers, "prov-",
                                  "provider", ref, label)

    def get_provider(self, actor, provider_id):
        self._check_role(actor, "read")
        return dict(self._provider(provider_id))

    def list_providers(self, actor):
        self._check_role(actor, "read")
        return [dict(p) for p in self._providers.values()]

    # -- auctions -----------------------------------------------------------

    @staticmethod
    def _auction_status(auction, moment):
        if auction["closed_at"] is not None:
            return "closed"
        if moment < _parse_moment(auction["opens_at"], "opens_at"):
            return "upcoming"
        if moment > _parse_moment(auction["closes_at"], "closes_at"):
            return "closed"
        return "open"

    def _auction_view(self, auction, now=None):
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        view = dict(auction)
        view["status"] = self._auction_status(auction, moment)
        view["bid_count"] = sum(
            1 for b in self._bids.values() if b["auction_id"] == auction["id"]
        )
        return view

    def create_auction(self, actor, customer_id, commodity, region,
                       unit_label, quantity_units, opens_at, closes_at):
        """Open an auction record for a customer. The auction's
        status is derived at read; nothing about its outcome is
        stored, ever."""
        self._check_role(actor, "conduct")
        self._customer(customer_id)
        _text(commodity, "commodity")
        _text(region, "region")
        _text(unit_label, "unit_label")
        if isinstance(quantity_units, bool) or not isinstance(quantity_units, int) \
                or quantity_units <= 0:
            raise ValidationError("quantity_units must be a positive integer")
        opens = _parse_moment(opens_at, "opens_at")
        closes = _parse_moment(closes_at, "closes_at")
        if closes < opens:
            raise ValidationError("closes_at must not precede opens_at")
        with self._lock:
            auction = {
                "id": self._mint("auc-"),
                "customer_id": customer_id,
                "commodity": commodity,
                "region": region,
                "unit_label": unit_label,
                "quantity_units": quantity_units,
                "opens_at": opens_at,
                "closes_at": closes_at,
                "closed_at": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._auctions[auction["id"]] = auction
        self._record(actor, "auction_create", auction["id"],
                     {"customer_id": customer_id})
        return self._auction_view(auction)

    def get_auction(self, actor, auction_id, now=None):
        self._check_role(actor, "read")
        return self._auction_view(self._auction(auction_id), now=now)

    def list_auctions(self, actor, customer_id=None, status=None, now=None):
        self._check_role(actor, "read")
        if customer_id is not None:
            self._customer(customer_id)
        if status is not None and status not in AUCTION_STATUSES:
            raise ValidationError("unknown auction status: %r" % (status,))
        result = []
        for auction in self._auctions.values():
            if customer_id is not None and auction["customer_id"] != customer_id:
                continue
            view = self._auction_view(auction, now=now)
            if status is not None and view["status"] != status:
                continue
            result.append(view)
        return result

    def close_auction(self, actor, auction_id, closed_at=None):
        """Record an early close of an auction. After this recorded
        action the derived status is ``closed`` at any clock."""
        self._check_role(actor, "conduct")
        auction = self._auction(auction_id)
        stamp = closed_at if closed_at is not None else _utc_now().isoformat()
        _parse_moment(stamp, "closed_at")
        with self._lock:
            if auction["closed_at"] is not None:
                raise ValidationError(
                    "auction %s was already closed at %s"
                    % (auction_id, auction["closed_at"])
                )
            auction["closed_at"] = stamp
        self._record(actor, "auction_close", auction_id, {"closed_at": stamp})
        return self._auction_view(auction, now=stamp)

    # -- bids and outcome -----------------------------------------------------

    def _check_auction_open(self, auction, moment):
        """Open-window seam: a bid is recorded only while the
        auction's derived status, at the bid's moment, is open."""
        status = self._auction_status(auction, moment)
        if status != "open":
            raise ValidationError(
                "auction %s is %r; bids are recorded only while it is open"
                % (auction["id"], status)
            )

    def record_bid(self, actor, auction_id, provider_id,
                   price_cents_per_unit, at=None):
        """Record a provider's bid on an auction. Bids are
        immutable: there is no update or delete."""
        self._check_role(actor, "conduct")
        auction = self._auction(auction_id)
        self._provider(provider_id)
        _price(price_cents_per_unit, "price_cents_per_unit")
        moment = _parse_moment(at, "at") if at is not None else _utc_now()
        self._check_auction_open(auction, moment)
        with self._lock:
            bid = {
                "id": self._mint("bid-"),
                "auction_id": auction_id,
                "provider_id": provider_id,
                "price_cents_per_unit": price_cents_per_unit,
                "seq": self._counters["bid-"],
                "created_by": actor_name(actor),
                "created_utc": moment.isoformat(),
            }
            self._bids[bid["id"]] = bid
        self._record(actor, "bid_record", bid["id"],
                     {"auction_id": auction_id, "provider_id": provider_id})
        return dict(bid)

    def list_bids(self, actor, auction_id):
        self._check_role(actor, "read")
        self._auction(auction_id)
        return [
            dict(b) for b in sorted(
                (b for b in self._bids.values() if b["auction_id"] == auction_id),
                key=lambda b: b["seq"],
            )
        ]

    def auction_outcome(self, actor, auction_id, now=None):
        """The auction's outcome, derived at read from its bid
        records: counts, the lowest price, and the winning bid
        (lowest price; ties by earliest sequence). Nothing about
        the outcome is stored. Before the auction closes the
        derived winner is provisional; ``is_final`` is true only
        when the derived status is ``closed``."""
        self._check_role(actor, "read")
        auction = self._auction(auction_id)
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        status = self._auction_status(auction, moment)
        bids = [b for b in self._bids.values() if b["auction_id"] == auction_id]
        winner = _derive_winner(bids)
        return {
            "auction_id": auction_id,
            "status": status,
            "is_final": status == "closed",
            "bid_count": len(bids),
            "provider_count": len({b["provider_id"] for b in bids}),
            "lowest_price_cents_per_unit": (
                winner["price_cents_per_unit"] if winner else None
            ),
            "winning_bid_id": winner["id"] if winner else None,
            "winning_provider_id": winner["provider_id"] if winner else None,
        }

    # -- price observations -----------------------------------------------------

    def record_observation(self, actor, region, commodity,
                           price_cents_per_unit, observed_at=None):
        """Record a price observation for a region/commodity series.
        These are the records price charts are drawn from."""
        self._check_role(actor, "observe")
        _text(region, "region")
        _text(commodity, "commodity")
        _price(price_cents_per_unit, "price_cents_per_unit", allow_zero=True)
        stamp = observed_at if observed_at is not None else _utc_now().isoformat()
        _parse_moment(stamp, "observed_at")
        with self._lock:
            observation = {
                "id": self._mint("obs-"),
                "region": region,
                "commodity": commodity,
                "price_cents_per_unit": price_cents_per_unit,
                "observed_at": stamp,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._observations[observation["id"]] = observation
        self._record(actor, "observation_record", observation["id"],
                     {"region": region, "commodity": commodity})
        return dict(observation)

    def list_observations(self, actor, region=None, commodity=None):
        self._check_role(actor, "read")
        return [
            dict(o) for o in self._observations.values()
            if (region is None or o["region"] == region)
            and (commodity is None or o["commodity"] == commodity)
        ]

    # -- alert subscriptions and alert records -----------------------------------

    def create_subscription(self, actor, customer_id, kind,
                            threshold_cents_per_unit=None,
                            region=None, commodity=None):
        """Subscribe a customer to a notification kind. Created
        active; the trigger-evaluation engine that would act on a
        subscription is Extended -- this is the subscription
        record."""
        self._check_role(actor, "alert")
        self._customer(customer_id)
        if kind not in NOTIFICATION_KINDS:
            raise ValidationError("unknown notification kind: %r" % (kind,))
        if threshold_cents_per_unit is not None:
            _price(threshold_cents_per_unit, "threshold_cents_per_unit",
                   allow_zero=True)
        _optional_text(region, "region")
        _optional_text(commodity, "commodity")
        with self._lock:
            subscription = {
                "id": self._mint("sub-"),
                "customer_id": customer_id,
                "kind": kind,
                "threshold_cents_per_unit": threshold_cents_per_unit,
                "region": region,
                "commodity": commodity,
                "active": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._subscriptions[subscription["id"]] = subscription
        self._record(actor, "subscription_create", subscription["id"],
                     {"customer_id": customer_id, "kind": kind})
        return dict(subscription)

    def deactivate_subscription(self, actor, subscription_id):
        """Deactivate a subscription by recorded action."""
        self._check_role(actor, "alert")
        subscription = self._subscriptions.get(subscription_id)
        if subscription is None:
            raise NotFoundError("no such subscription: %r" % (subscription_id,))
        with self._lock:
            if not subscription["active"]:
                raise ValidationError(
                    "subscription %s is already inactive" % subscription_id
                )
            subscription["active"] = False
        self._record(actor, "subscription_deactivate", subscription_id, {})
        return dict(subscription)

    def list_subscriptions(self, actor, customer_id=None, active=None):
        self._check_role(actor, "read")
        if customer_id is not None:
            self._customer(customer_id)
        return [
            dict(s) for s in self._subscriptions.values()
            if (customer_id is None or s["customer_id"] == customer_id)
            and (active is None or s["active"] == active)
        ]

    def record_alert(self, actor, customer_id, kind, subject,
                     subscription_id=None):
        """Record an alert issued to a customer. Delivery transport
        is Extended; what is recorded here is the alert itself."""
        self._check_role(actor, "alert")
        self._customer(customer_id)
        if kind not in NOTIFICATION_KINDS:
            raise ValidationError("unknown notification kind: %r" % (kind,))
        _text(subject, "subject")
        if subscription_id is not None:
            subscription = self._subscriptions.get(subscription_id)
            if subscription is None:
                raise NotFoundError(
                    "no such subscription: %r" % (subscription_id,))
            if subscription["customer_id"] != customer_id:
                raise ValidationError(
                    "subscription %s does not belong to customer %s"
                    % (subscription_id, customer_id)
                )
        with self._lock:
            alert = {
                "id": self._mint("alrt-"),
                "customer_id": customer_id,
                "kind": kind,
                "subject": subject,
                "subscription_id": subscription_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._alerts[alert["id"]] = alert
        self._record(actor, "alert_record", alert["id"],
                     {"customer_id": customer_id, "kind": kind})
        return dict(alert)

    def list_alerts(self, actor, customer_id=None, kind=None):
        self._check_role(actor, "read")
        if customer_id is not None:
            self._customer(customer_id)
        if kind is not None and kind not in NOTIFICATION_KINDS:
            raise ValidationError("unknown notification kind: %r" % (kind,))
        return [
            dict(a) for a in self._alerts.values()
            if (customer_id is None or a["customer_id"] == customer_id)
            and (kind is None or a["kind"] == kind)
        ]

    # -- advisory engagements ------------------------------------------------------

    def create_engagement(self, actor, customer_id, kind, note):
        """Record an advisory engagement of one of the claimed
        consulting kinds. The note is stored verbatim; the advice
        itself is Extended -- this is the engagement record."""
        self._check_role(actor, "advise")
        self._customer(customer_id)
        if kind not in ENGAGEMENT_KINDS:
            raise ValidationError("unknown engagement kind: %r" % (kind,))
        _text(note, "note")
        with self._lock:
            engagement = {
                "id": self._mint("eng-"),
                "customer_id": customer_id,
                "kind": kind,
                "note": note,
                "status": "open",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._engagements[engagement["id"]] = engagement
        self._record(actor, "engagement_create", engagement["id"],
                     {"customer_id": customer_id, "kind": kind})
        return dict(engagement)

    def close_engagement(self, actor, engagement_id):
        """Close an engagement by recorded action."""
        self._check_role(actor, "advise")
        engagement = self._engagements.get(engagement_id)
        if engagement is None:
            raise NotFoundError("no such engagement: %r" % (engagement_id,))
        with self._lock:
            if engagement["status"] == "closed":
                raise ValidationError(
                    "engagement %s is already closed" % engagement_id
                )
            engagement["status"] = "closed"
        self._record(actor, "engagement_close", engagement_id, {})
        return dict(engagement)

    def get_engagement(self, actor, engagement_id):
        self._check_role(actor, "read")
        engagement = self._engagements.get(engagement_id)
        if engagement is None:
            raise NotFoundError("no such engagement: %r" % (engagement_id,))
        return dict(engagement)

    def list_engagements(self, actor, customer_id=None, kind=None, status=None):
        self._check_role(actor, "read")
        if customer_id is not None:
            self._customer(customer_id)
        if kind is not None and kind not in ENGAGEMENT_KINDS:
            raise ValidationError("unknown engagement kind: %r" % (kind,))
        if status is not None and status not in ENGAGEMENT_STATUSES:
            raise ValidationError("unknown engagement status: %r" % (status,))
        return [
            dict(e) for e in self._engagements.values()
            if (customer_id is None or e["customer_id"] == customer_id)
            and (kind is None or e["kind"] == kind)
            and (status is None or e["status"] == status)
        ]

    def audit_read(self, actor):
        """Return the audit trail. Requires the ``audit_read``
        permission (admin-only in the permission matrix)."""
        self._check_role(actor, "audit_read")
        entries = self.audit.entries() if self.audit is not None else []
        return {"entries": entries, "count": len(entries)}

    # -- search and summary -----------------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over customers
        and providers (ref and label), auctions (commodity and
        region), and engagement notes."""
        self._check_role(actor, "read")
        _text(query, "query")
        needle = query.lower()
        customers = [
            dict(c) for c in self._customers.values()
            if needle in c["ref"].lower() or needle in c["label"].lower()
        ]
        providers = [
            dict(p) for p in self._providers.values()
            if needle in p["ref"].lower() or needle in p["label"].lower()
        ]
        auctions = [
            self._auction_view(a) for a in self._auctions.values()
            if needle in a["commodity"].lower() or needle in a["region"].lower()
        ]
        engagements = [
            dict(e) for e in self._engagements.values()
            if needle in e["note"].lower()
        ]
        return {
            "customers": customers,
            "providers": providers,
            "auctions": auctions,
            "engagements": engagements,
        }

    def summary(self, actor, now=None):
        """Counts over the whole registry, computed on read from
        records only. The latest price per observation series is a
        recorded value selected by observed moment -- never a
        computed score."""
        self._check_role(actor, "read")
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        by_status = {status: 0 for status in AUCTION_STATUSES}
        for auction in self._auctions.values():
            by_status[self._auction_status(auction, moment)] += 1
        latest = {}
        for observation in self._observations.values():
            key = "%s|%s" % (observation["region"], observation["commodity"])
            current = latest.get(key)
            candidate = (
                _parse_moment(observation["observed_at"], "observed_at"),
                observation["price_cents_per_unit"],
                observation["observed_at"],
                observation["id"],
            )
            if current is None or candidate[0] >= current[0]:
                latest[key] = candidate
        alerts_by_kind = {kind: 0 for kind in NOTIFICATION_KINDS}
        for alert in self._alerts.values():
            alerts_by_kind[alert["kind"]] += 1
        engagements_by_kind = {kind: 0 for kind in ENGAGEMENT_KINDS}
        engagements_open = 0
        for engagement in self._engagements.values():
            engagements_by_kind[engagement["kind"]] += 1
            if engagement["status"] == "open":
                engagements_open += 1
        return {
            "customers": len(self._customers),
            "providers": len(self._providers),
            "auctions_by_status": by_status,
            "bids": len(self._bids),
            "observations": len(self._observations),
            "latest_prices": {
                key: {
                    "price_cents_per_unit": value[1],
                    "observed_at": value[2],
                    "observation_id": value[3],
                }
                for key, value in sorted(latest.items())
            },
            "subscriptions_active": sum(
                1 for s in self._subscriptions.values() if s["active"]
            ),
            "alerts_by_kind": alerts_by_kind,
            "engagements_by_kind": engagements_by_kind,
            "engagements_open": engagements_open,
        }
