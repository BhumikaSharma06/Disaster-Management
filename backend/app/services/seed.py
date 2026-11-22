"""Optional database seed script; geography records remain unverified prototypes."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.alert import Alert
from app.models.hazard_risk_score import HazardRiskScore
from app.models.match import Match
from app.models.region import Region
from app.models.shelter import Shelter
from app.models.sos_request import SOSRequest
from app.models.volunteer_offer import VolunteerOffer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Find repository root directory
REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_FILE = REPO_ROOT / "ml" / "data" / "raw" / "bihar_sw_daily_discharge_manual.csv"

# Unverified prototype polygons for configured study-area districts (SRID 4326).
DISTRICT_BOUNDARIES = {
    "Supaul": {
        "name": "Supaul",
        "district_name": "Supaul",
        "region_type": "district",
        "wkt": "MULTIPOLYGON(((86.58 25.95, 87.12 25.95, 87.12 26.65, 86.58 26.65, 86.58 25.95)))",
    },
    "Saharsa": {
        "name": "Saharsa",
        "district_name": "Saharsa",
        "region_type": "district",
        "wkt": "MULTIPOLYGON(((86.35 25.65, 86.85 25.65, 86.85 26.05, 86.35 26.05, 86.35 25.65)))",
    },
    "Madhepura": {
        "name": "Madhepura",
        "district_name": "Madhepura",
        "region_type": "district",
        "wkt": "MULTIPOLYGON(((86.65 25.55, 87.15 25.55, 87.15 26.15, 86.65 26.15, 86.65 25.55)))",
    },
    "Purnia": {
        "name": "Purnia",
        "district_name": "Purnia",
        "region_type": "district",
        "wkt": "MULTIPOLYGON(((87.10 25.50, 87.85 25.50, 87.85 26.10, 87.10 26.10, 87.10 25.50)))",
    },
}

# Unverified prototype shelter records; source validation is still required.
SHELTERS_DATA = [
    # Supaul shelters
    {
        "district": "Supaul",
        "name": "Birpur Model High School & Flood Shelter",
        "capacity": 600,
        "lon": 86.9350,
        "lat": 26.5200,
    },
    {
        "district": "Supaul",
        "name": "Supaul Zila High School Relief Centre",
        "capacity": 850,
        "lon": 86.6050,
        "lat": 26.1260,
    },
    {
        "district": "Supaul",
        "name": "Nirmali Community Disaster Centre",
        "capacity": 450,
        "lon": 86.5920,
        "lat": 26.3150,
    },
    {
        "district": "Supaul",
        "name": "Pipra Block Relief Camp",
        "capacity": 400,
        "lon": 86.7200,
        "lat": 26.1800,
    },
    # Saharsa shelters
    {
        "district": "Saharsa",
        "name": "Saharsa Stadium Emergency Relief Camp",
        "capacity": 1200,
        "lon": 86.5980,
        "lat": 25.8830,
    },
    {
        "district": "Saharsa",
        "name": "Simri Bakhtiarpur High School",
        "capacity": 600,
        "lon": 86.5830,
        "lat": 25.7500,
    },
    {
        "district": "Saharsa",
        "name": "Nauhatta Panchayat Bhawan Shelter",
        "capacity": 350,
        "lon": 86.4900,
        "lat": 25.9800,
    },
    {
        "district": "Saharsa",
        "name": "Mahishi Community Health Centre",
        "capacity": 400,
        "lon": 86.4500,
        "lat": 25.8500,
    },
    # Madhepura shelters
    {
        "district": "Madhepura",
        "name": "Madhepura Town Hall & Relief Camp",
        "capacity": 750,
        "lon": 86.7900,
        "lat": 25.9220,
    },
    {
        "district": "Madhepura",
        "name": "Alamnagar High School Flood Shelter",
        "capacity": 500,
        "lon": 86.9000,
        "lat": 25.5500,
    },
    {
        "district": "Madhepura",
        "name": "Chausa Community Disaster Relief Camp",
        "capacity": 400,
        "lon": 87.0200,
        "lat": 25.5200,
    },
    # Purnia shelters
    {
        "district": "Purnia",
        "name": "Purnia Zila School Relief Center",
        "capacity": 1000,
        "lon": 87.4700,
        "lat": 25.7800,
    },
    {
        "district": "Purnia",
        "name": "Baisi Flood Evacuation Centre",
        "capacity": 600,
        "lon": 87.7500,
        "lat": 25.8333,
    },
    {
        "district": "Purnia",
        "name": "Dagarua High School Disaster Shelter",
        "capacity": 450,
        "lon": 87.6000,
        "lat": 25.8000,
    },
    {
        "district": "",
        "name": "Guwahati Community Shelter",
        "capacity": 900,
        "lon": 91.7362,
        "lat": 26.1445,
    },
    {
        "district": "",
        "name": "Kolkata East Emergency Shelter",
        "capacity": 1200,
        "lon": 88.3639,
        "lat": 22.5726,
    },
    {
        "district": "",
        "name": "Rajahmundry Cyclone Relief Centre",
        "capacity": 800,
        "lon": 81.7667,
        "lat": 16.9667,
    },
    {
        "district": "",
        "name": "Machilipatnam Coastal Shelter",
        "capacity": 700,
        "lon": 81.1400,
        "lat": 16.1800,
    },
    {
        "district": "",
        "name": "Bhubaneswar District Emergency Centre",
        "capacity": 1100,
        "lon": 85.8245,
        "lat": 20.2961,
    },
    {
        "district": "",
        "name": "Indore Civic Relief Centre",
        "capacity": 650,
        "lon": 75.8577,
        "lat": 22.7196,
    },
    {
        "district": "",
        "name": "Delhi West Emergency Assembly Centre",
        "capacity": 1500,
        "lon": 77.2090,
        "lat": 28.6139,
    },
    {
        "district": "",
        "name": "Ahmedabad Civil Shelter",
        "capacity": 900,
        "lon": 72.8311,
        "lat": 21.1702,
    },
    {
        "district": "",
        "name": "Chennai Coast Relief Centre",
        "capacity": 1300,
        "lon": 80.2707,
        "lat": 13.0827,
    },
    {
        "district": "",
        "name": "Aurangabad Marathwada Relief Centre",
        "capacity": 600,
        "lon": 75.3433,
        "lat": 19.8762,
    },
    {
        "district": "",
        "name": "Anantapur Drought Relief Centre",
        "capacity": 550,
        "lon": 77.6006,
        "lat": 14.6819,
    },
    {
        "district": "",
        "name": "Jhansi Bundelkhand Shelter",
        "capacity": 700,
        "lon": 78.6115,
        "lat": 25.4358,
    },
]


def seed_regions(session: Session) -> dict[str, Region]:
    """Seed unverified prototype districts and return a lookup dictionary."""
    existing_regions = {r.name: r for r in session.query(Region).all()}
    regions_map: dict[str, Region] = {}

    for district_name, data in DISTRICT_BOUNDARIES.items():
        if district_name in existing_regions:
            regions_map[district_name] = existing_regions[district_name]
            logger.info("Region %s already exists.", district_name)
        else:
            region = Region(
                name=data["name"],
                district_name=data["district_name"],
                region_type=data["region_type"],
                boundary=WKTElement(data["wkt"], srid=4326),
                source_name="Unverified project seed data",
                source_reference="backend/app/services/seed.py",
            )
            session.add(region)
            session.flush()
            regions_map[district_name] = region
            logger.info("Created Region: %s (ID: %s)", district_name, region.id)

    return regions_map


def seed_shelters(session: Session, regions_map: dict[str, Region]) -> list[Shelter]:
    """Seed unverified prototype shelter records."""
    existing_names = {s.name for s in session.query(Shelter.name).all()}
    created_shelters: list[Shelter] = []

    for shelter_info in SHELTERS_DATA:
        if shelter_info["name"] in existing_names:
            continue

        region = regions_map.get(shelter_info["district"])
        point_wkt = f"POINT({shelter_info['lon']} {shelter_info['lat']})"

        shelter = Shelter(
            name=shelter_info["name"],
            region_id=region.id if region else None,
            capacity=shelter_info["capacity"],
            current_occupancy=0,
            location=WKTElement(point_wkt, srid=4326),
            source_name="Unverified project seed data",
            source_reference="backend/app/services/seed.py",
        )
        session.add(shelter)
        created_shelters.append(shelter)

    session.flush()
    logger.info("Seeded %d emergency shelters.", len(created_shelters))
    return created_shelters


def seed_birpur_discharge_and_risk(session: Session, regions_map: dict[str, Region]) -> int:
    """Calculate and seed hazard risk scores from real Birpur Barrage discharge records."""
    if not RAW_DATA_FILE.exists():
        logger.warning(
            "Raw discharge file not found at %s. Skipping discharge scores.", RAW_DATA_FILE
        )
        return 0

    df = pd.read_csv(RAW_DATA_FILE)
    birpur = df[df["Site"] == "Birpur Barrage"].copy()
    if birpur.empty:
        logger.warning("No Birpur Barrage records found in raw CSV.")
        return 0

    birpur["ParsedDate"] = pd.to_datetime(birpur["Date"], format="%d-%m-%Y", errors="coerce")
    birpur = birpur.dropna(subset=["ParsedDate", "Discharge (M3/s)"]).sort_values("ParsedDate")

    # Take the 60 most recent continuous observations
    sample_records = birpur.tail(60)
    score_count = 0

    # Operational calibration thresholds for Kosi at Birpur Barrage:
    # Lean flow: < 1500 m3/s -> score ~ 0.10 - 0.25
    # High flow: 4500 m3/s (Warning level) -> score ~ 0.60
    # Extreme discharge: 8000+ m3/s (Danger level) -> score ~ 0.85 - 1.00
    for _, row in sample_records.iterrows():
        discharge = float(row["Discharge (M3/s)"])
        scored_at = row["ParsedDate"].to_pydatetime()

        # Compute baseline flood risk ratio
        base_score = min(1.0, max(0.1, round(discharge / 8000.0, 3)))

        # Hydrologic attenuation factors moving downstream:
        # Supaul: immediate upstream impact (1.0x)
        # Saharsa: (0.9x)
        # Madhepura: (0.85x)
        # Purnia: (0.75x)
        district_weights = {
            "Supaul": 1.0,
            "Saharsa": 0.90,
            "Madhepura": 0.85,
            "Purnia": 0.75,
        }

        for district_name, weight in district_weights.items():
            region = regions_map.get(district_name)
            if not region:
                continue

            calibrated_score = round(min(1.0, base_score * weight), 3)

            # Check if score already exists for region and timestamp
            existing = (
                session.query(HazardRiskScore.id)
                .filter_by(
                    region_id=region.id,
                    hazard_type="flood",
                    scored_at=scored_at,
                )
                .first()
            )
            if not existing:
                risk_entry = HazardRiskScore(
                    region_id=region.id,
                    hazard_type="flood",
                    score=calibrated_score,
                    scored_at=scored_at,
                )
                session.add(risk_entry)
                score_count += 1

    session.flush()
    logger.info("Seeded %d calibrated flood risk score records.", score_count)
    return score_count


def seed_alerts(session: Session) -> list[Alert]:
    """Seed multilingual emergency alerts (English, Hindi, Maithili)."""
    if session.query(Alert).count() > 0:
        logger.info("Alerts already exist. Skipping.")
        return []

    alerts_data = [
        {
            "hazard_type": "flood",
            "language": "en",
            "message": (
                "Flood Advisory: Significant upstream discharge observed at Birpur Barrage. "
                "Low-lying areas along the Kosi embankments in Supaul and Saharsa should prepare "
                "for water level rise and verify designated shelter routes."
            ),
            "delivery_status": "delivered",
        },
        {
            "hazard_type": "flood",
            "language": "hi",
            "message": (
                "बाढ़ चेतावनी: बीरपुर बैराज पर ऊपरी जलप्रवाह में वृद्धि दर्ज की गई है। "
                "सुपौल और सहरसा में कोसी तटबंध के निचले इलाकों के निवासियों को जलस्तर बढ़ने "
                "की संभावना के मद्देनजर सतर्क रहने और नजदीकी सुरक्षित आश्रय स्थलों की "
                "जानकारी रखने की सलाह दी जाती है।"
            ),
            "delivery_status": "delivered",
        },
        {
            "hazard_type": "flood",
            "language": "mai",
            "message": (
                "बाढ़ि चेतावनी: बीरपुर बैराज पर ऊपरी पानि बहाव मे वृद्धि देखल गेल अछि। "
                "सुपौल आ सहरसा मे कोसी तटबंधक निचुलका इलाकाक लोक सभकेँ सतर्क रहबाक आ नजदीकी "
                "सुरक्षित शरणस्थल केर जानकारी रखबाक सलाह देल जाइत अछि।"
            ),
            "delivery_status": "delivered",
        },
    ]

    created_alerts = []
    for data in alerts_data:
        alert = Alert(
            hazard_type=data["hazard_type"],
            language=data["language"],
            message=data["message"],
            delivery_status=data["delivery_status"],
            created_at=datetime.utcnow(),
        )
        session.add(alert)
        created_alerts.append(alert)

    session.flush()
    logger.info("Seeded %d multilingual flood alerts.", len(created_alerts))
    return created_alerts


def seed_sos_and_volunteers(session: Session) -> None:
    """Seed realistic initial SOS requests and volunteer offers for demonstration."""
    if session.query(SOSRequest).count() > 0:
        logger.info("SOS requests already exist. Skipping.")
        return

    # Sample SOS Request in Supaul
    sos = SOSRequest(
        need_type="medical_evacuation",
        description=(
            "Elderly citizen needing immediate medical evacuation "
            "from flooded village near Nirmali."
        ),
        urgency="high",
        status="open",
        location=WKTElement("POINT(86.5950 26.3100)", srid=4326),
    )
    session.add(sos)
    session.flush()

    # Sample Volunteer Offer in Supaul
    volunteer = VolunteerOffer(
        capacity_type="rescue_boat",
        description=(
            "Motorized rescue boat with 6 life jackets stationed at Nirmali block headquarters."
        ),
        capacity=6,
        status="available",
        location=WKTElement("POINT(86.5920 26.3150)", srid=4326),
    )
    session.add(volunteer)
    session.flush()

    # Sample Match
    match = Match(
        sos_request_id=sos.id,
        volunteer_offer_id=volunteer.id,
        distance_km=0.65,
        status="proposed",
    )
    session.add(match)
    session.flush()
    logger.info("Seeded sample SOS request, volunteer capacity, and proposed match.")


def run_seed() -> None:
    """Seed data into a database whose schema has already been migrated."""
    session = SessionLocal()
    try:
        logger.info("Starting seed process; geography records are unverified prototypes.")
        regions_map = seed_regions(session)
        seed_shelters(session, regions_map)
        seed_birpur_discharge_and_risk(session, regions_map)
        seed_alerts(session)
        seed_sos_and_volunteers(session)
        session.commit()
        logger.info("Database seeding completed successfully.")
    except Exception as e:
        session.rollback()
        logger.error("Seeding failed: %s", e)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_seed()
