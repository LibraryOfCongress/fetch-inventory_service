"""
Building-level ILS service point override (FLIT multi-facility fix).

A single Owner's ILSConfiguration.ils_service_point_id is a single, per-Owner
default. When that Owner's items are distributed across multiple physical
Buildings (e.g. Fort Meade and Cabin Branch), shelving/picklist check-ins must
resolve the *physical building's* mapped service point (scoped per
ILSConfiguration, via BuildingILSServicePoint) and pass it down to the
adapter as an override, rather than always falling back to the Owner's single
configured service point.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.ils.tasks import check_in_picklist_item_async, check_in_shelved_item_async
from app.models.barcode_types import BarcodeType
from app.models.barcodes import Barcode
from app.models.buildings import Building
from app.models.building_ils_service_points import BuildingILSServicePoint
from app.models.ils_configurations import AdapterTypeEnum, ILSConfiguration
from app.models.items import Item
from app.models.owner_tiers import OwnerTier
from app.models.owners import Owner
from app.models.pick_lists import PickList, PickListStatus
from app.models.shelving_jobs import OriginStatus, ShelvingJob, ShelvingJobStatus
from app.models.size_class import SizeClass


def _u(prefix, length):
    return f"{prefix}{uuid.uuid4().hex[:8]}"[:length]


def _make_ils_config(session, **hooks):
    cfg = ILSConfiguration(
        name=_u("CFG", 150),
        adapter_type=AdapterTypeEnum.CUSTOM_MIDDLEWARE,
        base_url="http://mock",
        tenant_id="t",
        auth_client_id="c",
        auth_client_secret="s",
        is_active=True,
        ils_service_point_id="OWNER-DEFAULT-SP",
        **hooks,
    )
    session.add(cfg)
    session.commit()
    return cfg


def _make_owner_with_config(session, cfg):
    tier = session.query(OwnerTier).first()
    assert tier is not None, "seed must provide an OwnerTier"
    o = Owner(name=_u("OW", 40), owner_tier_id=tier.id, ils_configuration_id=cfg.id)
    session.add(o)
    session.commit()
    return o


def _make_building(session):
    b = Building(name=_u("B", 25))
    session.add(b)
    session.commit()
    return b


def _map_building_service_point(session, building, cfg, service_point_id):
    mapping = BuildingILSServicePoint(
        building_id=building.id,
        ils_configuration_id=cfg.id,
        ils_service_point_id=service_point_id,
    )
    session.add(mapping)
    session.commit()
    return mapping


def _make_item(session, owner, barcode_value):
    bt = session.query(BarcodeType).filter_by(name="Item").first() \
        or session.query(BarcodeType).first()
    sc = session.query(SizeClass).first()
    bc = Barcode(value=barcode_value, type_id=bt.id, withdrawn=False)
    session.add(bc)
    session.commit()
    item = Item(barcode_id=bc.id, owner_id=owner.id, size_class_id=sc.id)
    session.add(item)
    session.commit()
    return item


def test_shelving_checkin_uses_building_service_point_override(session: Session, test_database):
    cfg = _make_ils_config(session, enable_shelving_hook=True)
    owner = _make_owner_with_config(session, cfg)
    building = _make_building(session)
    _map_building_service_point(session, building, cfg, "FORT-MEADE-SP")
    barcode_value = f"MOCK-{uuid.uuid4().hex[:8]}"
    _make_item(session, owner, barcode_value)

    shelving_job = ShelvingJob(
        status=ShelvingJobStatus.Running,
        origin=OriginStatus.Direct,
        building_id=building.id,
        last_transition=datetime.now(timezone.utc),
    )
    session.add(shelving_job)
    session.commit()

    fake_adapter = MagicMock()
    fake_adapter.check_in_item.return_value = MagicMock(
        success=True, raw_status_string=cfg.expected_shelved_status, error_message=None
    )

    with patch("app.ils.tasks.get_ils_adapter", return_value=fake_adapter):
        check_in_shelved_item_async(
            barcode_value=barcode_value,
            owner_id=owner.id,
            is_non_tray=False,
            shelving_job_id=shelving_job.id,
        )

    fake_adapter.check_in_item.assert_called_once_with(
        barcode_value, service_point_override="FORT-MEADE-SP"
    )


def test_shelving_checkin_falls_back_when_building_has_no_mapping(session: Session, test_database):
    cfg = _make_ils_config(session, enable_shelving_hook=True)
    owner = _make_owner_with_config(session, cfg)
    building = _make_building(session)  # no BuildingILSServicePoint row for this cfg
    barcode_value = f"MOCK-{uuid.uuid4().hex[:8]}"
    _make_item(session, owner, barcode_value)

    shelving_job = ShelvingJob(
        status=ShelvingJobStatus.Running,
        origin=OriginStatus.Direct,
        building_id=building.id,
        last_transition=datetime.now(timezone.utc),
    )
    session.add(shelving_job)
    session.commit()

    fake_adapter = MagicMock()
    fake_adapter.check_in_item.return_value = MagicMock(
        success=True, raw_status_string=cfg.expected_shelved_status, error_message=None
    )

    with patch("app.ils.tasks.get_ils_adapter", return_value=fake_adapter):
        check_in_shelved_item_async(
            barcode_value=barcode_value,
            owner_id=owner.id,
            is_non_tray=False,
            shelving_job_id=shelving_job.id,
        )

    # No BuildingILSServicePoint mapping for this (building, config) pair ->
    # adapter falls back to the Owner-level default internally (None is
    # passed through explicitly).
    fake_adapter.check_in_item.assert_called_once_with(
        barcode_value, service_point_override=None
    )


def test_picklist_checkin_uses_building_service_point_override(session: Session, test_database):
    cfg = _make_ils_config(session, enable_picklist_hook=True)
    owner = _make_owner_with_config(session, cfg)
    building = _make_building(session)
    _map_building_service_point(session, building, cfg, "CABIN-BRANCH-SP")
    barcode_value = f"MOCK-{uuid.uuid4().hex[:8]}"
    _make_item(session, owner, barcode_value)

    pick_list = PickList(
        status=PickListStatus.Running,
        building_id=building.id,
        last_transition=datetime.now(timezone.utc),
    )
    session.add(pick_list)
    session.commit()

    fake_adapter = MagicMock()
    fake_adapter.check_in_item.return_value = MagicMock(
        success=True, raw_status_string=cfg.expected_picklist_status, error_message=None
    )

    with patch("app.ils.tasks.get_ils_adapter", return_value=fake_adapter):
        check_in_picklist_item_async(
            barcode_value=barcode_value,
            owner_id=owner.id,
            is_non_tray=False,
            pick_list_id=pick_list.id,
        )

    fake_adapter.check_in_item.assert_called_once_with(
        barcode_value, service_point_override="CABIN-BRANCH-SP"
    )


def test_building_service_point_is_scoped_per_ils_configuration(session: Session, test_database):
    # Same building, two different ILS integrations -> two different mapped
    # service points. This is exactly the case the Building-column design
    # couldn't represent (only one column, no room for a second integration).
    cfg_a = _make_ils_config(session, enable_shelving_hook=True)
    cfg_b = _make_ils_config(session, enable_shelving_hook=True)
    building = _make_building(session)
    _map_building_service_point(session, building, cfg_a, "SP-FOR-CONFIG-A")
    _map_building_service_point(session, building, cfg_b, "SP-FOR-CONFIG-B")

    owner_a = _make_owner_with_config(session, cfg_a)
    barcode_value = f"MOCK-{uuid.uuid4().hex[:8]}"
    _make_item(session, owner_a, barcode_value)

    shelving_job = ShelvingJob(
        status=ShelvingJobStatus.Running,
        origin=OriginStatus.Direct,
        building_id=building.id,
        last_transition=datetime.now(timezone.utc),
    )
    session.add(shelving_job)
    session.commit()

    fake_adapter = MagicMock()
    fake_adapter.check_in_item.return_value = MagicMock(
        success=True, raw_status_string=cfg_a.expected_shelved_status, error_message=None
    )

    with patch("app.ils.tasks.get_ils_adapter", return_value=fake_adapter):
        check_in_shelved_item_async(
            barcode_value=barcode_value,
            owner_id=owner_a.id,
            is_non_tray=False,
            shelving_job_id=shelving_job.id,
        )

    fake_adapter.check_in_item.assert_called_once_with(
        barcode_value, service_point_override="SP-FOR-CONFIG-A"
    )
