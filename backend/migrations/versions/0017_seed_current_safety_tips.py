"""Move the existing hazard guides into administrator-managed safety tips."""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_seed_current_safety_tips"
down_revision: str | None = "0016_super_admin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TIPS = [
    ("flood", "Flood", "before", "Track local water and weather advisories."),
    ("flood", "Flood", "before", "Move medicines, documents, and essential supplies to a dry, elevated place."),
    ("flood", "Flood", "during", "Move to higher ground when advised."),
    ("flood", "Flood", "during", "Never walk, swim, or drive through floodwater."),
    ("flood", "Flood", "during", "Stay away from fallen power lines and electrical equipment in water."),
    ("flood", "Flood", "after", "Return only when authorities say it is safe."),
    ("flood", "Flood", "after", "Avoid floodwater and damaged buildings; use safe drinking water."),
    ("cyclone", "Cyclone", "before", "Follow official weather bulletins and evacuation instructions."),
    ("cyclone", "Cyclone", "before", "Secure loose outdoor items and keep essential medicines, water, and documents ready."),
    ("cyclone", "Cyclone", "during", "Stay indoors, away from windows and glass."),
    ("cyclone", "Cyclone", "during", "Do not go outside during a lull; strong winds may return."),
    ("cyclone", "Cyclone", "during", "Move to an official shelter if instructed."),
    ("cyclone", "Cyclone", "after", "Wait for the official all-clear before going outside or returning home."),
    ("cyclone", "Cyclone", "after", "Avoid floodwater, damaged structures, and fallen power lines."),
    ("earthquake", "Earthquake", "before", "Secure heavy furniture and identify safe cover away from windows."),
    ("earthquake", "Earthquake", "before", "Keep shoes, a torch, water, and essential medicines accessible."),
    ("earthquake", "Earthquake", "during", "Drop, cover, and hold on; protect your head and neck."),
    ("earthquake", "Earthquake", "during", "Stay indoors away from windows; if outside, move to an open area away from buildings and wires."),
    ("earthquake", "Earthquake", "during", "Do not use lifts."),
    ("earthquake", "Earthquake", "after", "Expect aftershocks and leave damaged buildings carefully."),
    ("earthquake", "Earthquake", "after", "Check for injuries and hazards; follow official instructions."),
    ("landslide", "Landslide", "before", "Watch for official warnings and signs such as new ground cracks or tilting trees."),
    ("landslide", "Landslide", "before", "Know more than one way to leave the area."),
    ("landslide", "Landslide", "during", "Move quickly away from the path of moving soil, rocks, or debris if safe to do so."),
    ("landslide", "Landslide", "during", "Avoid valleys, stream channels, and bridges near the slide."),
    ("landslide", "Landslide", "after", "Stay away from the slide area; additional movement may follow."),
    ("landslide", "Landslide", "after", "Report damaged utilities and follow local authority guidance."),
    ("drought", "Drought", "before", "Follow local water-use advisories and store drinking water safely."),
    ("drought", "Drought", "before", "Plan for livestock, crops, and people who may need extra water support."),
    ("drought", "Drought", "during", "Use safe drinking water and follow public health advisories."),
    ("drought", "Drought", "during", "Seek local assistance if household water or essential supplies run low."),
    ("drought", "Drought", "during", "Avoid open flames where vegetation is dry."),
    ("drought", "Drought", "after", "Follow local guidance on water quality and rationing."),
    ("drought", "Drought", "after", "Resume agricultural or water use according to local advisories."),
    ("heatwave", "Heatwave", "before", "Check local heat advisories and identify a cool place to go."),
    ("heatwave", "Heatwave", "before", "Plan outdoor work for cooler hours and check on people at higher risk."),
    ("heatwave", "Heatwave", "during", "Move to a cool or shaded place, rest, and drink water regularly if safe to do so."),
    ("heatwave", "Heatwave", "during", "Wear light clothing and avoid strenuous activity during the hottest hours."),
    ("heatwave", "Heatwave", "during", "Confusion, fainting, or very high body temperature needs urgent medical help."),
    ("heatwave", "Heatwave", "after", "Seek medical care if symptoms continue or worsen."),
    ("heatwave", "Heatwave", "after", "Continue checking on vulnerable people as advised by health authorities."),
    ("tsunami", "Tsunami", "before", "Know the route to high ground and follow tsunami warning information."),
    ("tsunami", "Tsunami", "before", "After strong or long coastal shaking, be ready to move inland or uphill."),
    ("tsunami", "Tsunami", "during", "Move to high ground or inland immediately when warned or after strong coastal shaking."),
    ("tsunami", "Tsunami", "during", "Stay away from beaches, estuaries, and waterways; do not wait to watch the waves."),
    ("tsunami", "Tsunami", "after", "Remain in a safe area until authorities issue an all-clear."),
    ("tsunami", "Tsunami", "after", "Expect multiple waves and follow official return instructions."),
    ("wildfire", "Wildfire", "before", "Know local evacuation routes and keep essential items ready."),
    ("wildfire", "Wildfire", "before", "Clear dry leaves and combustible material around the home where safe and permitted."),
    ("wildfire", "Wildfire", "during", "Leave early when authorities advise evacuation; follow their route instructions."),
    ("wildfire", "Wildfire", "during", "Avoid smoke and do not enter a fire area to retrieve belongings."),
    ("wildfire", "Wildfire", "during", "If trapped, call emergency services and follow dispatcher instructions."),
    ("wildfire", "Wildfire", "after", "Return only after authorities declare the area safe."),
    ("wildfire", "Wildfire", "after", "Avoid hot spots, damaged trees, and downed power lines."),
    ("lightning", "Lightning", "before", "Check thunderstorm advisories and identify a substantial enclosed shelter."),
    ("lightning", "Lightning", "before", "Pause outdoor activity when thunder is heard."),
    ("lightning", "Lightning", "during", "Go indoors or into a hard-topped vehicle; avoid open fields, isolated trees, and water."),
    ("lightning", "Lightning", "during", "If no shelter is available, crouch low with feet together; do not lie flat."),
    ("lightning", "Lightning", "during", "Wait 30 minutes after the last thunder before resuming outdoor activity."),
    ("lightning", "Lightning", "after", "Avoid damaged power lines and report fires or injuries."),
    ("lightning", "Lightning", "after", "Give first aid if trained and call emergency services for serious injuries."),
    ("severe-storm", "Severe storm", "before", "Follow weather warnings and secure loose outdoor objects."),
    ("severe-storm", "Severe storm", "before", "Identify an interior room away from windows."),
    ("severe-storm", "Severe storm", "during", "Stay indoors and away from glass; move to a sturdy interior space."),
    ("severe-storm", "Severe storm", "during", "Avoid travel, underpasses, and areas with fallen wires or debris."),
    ("severe-storm", "Severe storm", "during", "Follow evacuation instructions if flooding or structural danger develops."),
    ("severe-storm", "Severe storm", "after", "Wait for official safety updates before travelling."),
    ("severe-storm", "Severe storm", "after", "Avoid downed wires, damaged buildings, and flooded roads."),
    ("avalanche", "Avalanche", "before", "Check official mountain and snow advisories before travel."),
    ("avalanche", "Avalanche", "before", "Avoid closed slopes and follow local route restrictions."),
    ("avalanche", "Avalanche", "during", "Move out of the slide path if possible and alert others."),
    ("avalanche", "Avalanche", "during", "Once safe, contact emergency rescue services and provide the location."),
    ("avalanche", "Avalanche", "after", "Do not re-enter the slide area; further avalanches may occur."),
    ("avalanche", "Avalanche", "after", "Leave rescue operations to trained teams and follow official instructions."),
    ("industrial-incident", "Industrial or chemical incident", "before", "Know local warning signals and the nearest official shelter guidance."),
    ("industrial-incident", "Industrial or chemical incident", "before", "Keep essential medicines and emergency contacts accessible."),
    ("industrial-incident", "Industrial or chemical incident", "during", "Follow official evacuation or shelter-in-place instructions immediately."),
    ("industrial-incident", "Industrial or chemical incident", "during", "Avoid the visible plume or spill area; do not touch unknown substances."),
    ("industrial-incident", "Industrial or chemical incident", "during", "Call emergency services and share your location and observed hazard."),
    ("industrial-incident", "Industrial or chemical incident", "after", "Do not return until authorities declare the area safe."),
    ("industrial-incident", "Industrial or chemical incident", "after", "Follow public health instructions about exposure, cleanup, and water safety."),
    ("public-health", "Public-health emergency", "before", "Follow advisories from public-health authorities."),
    ("public-health", "Public-health emergency", "before", "Keep essential medicines and verified health-service contacts available."),
    ("public-health", "Public-health emergency", "during", "Use trusted health sources and follow current prevention advice."),
    ("public-health", "Public-health emergency", "during", "Seek medical care for severe symptoms; call emergency services for immediate danger."),
    ("public-health", "Public-health emergency", "during", "Avoid spreading unverified reports."),
    ("public-health", "Public-health emergency", "after", "Continue health precautions for the period advised by authorities."),
    ("public-health", "Public-health emergency", "after", "Use official channels for care, recovery support, and updated guidance."),
    ("cold-wave", "Cold wave", "before", "Check local cold-weather advisories and prepare warm clothing and bedding."),
    ("cold-wave", "Cold wave", "before", "Check on older adults, infants, and people without reliable shelter."),
    ("cold-wave", "Cold wave", "during", "Stay warm and dry; use heating equipment only as directed and ventilate fuel-burning devices."),
    ("cold-wave", "Cold wave", "during", "Seek a warm shelter if your home is unsafe or unheated."),
    ("cold-wave", "Cold wave", "during", "Call emergency services for suspected hypothermia or immediate danger."),
    ("cold-wave", "Cold wave", "after", "Continue local precautions while low temperatures persist."),
    ("cold-wave", "Cold wave", "after", "Get medical advice for cold-related symptoms."),
]


def upgrade() -> None:
    """Seed all existing frontend guidance as published English records."""
    safety_tips = sa.table(
        "safety_tips",
        sa.column("title", sa.String),
        sa.column("content", sa.Text),
        sa.column("hazard_type", sa.String),
        sa.column("phase", sa.String),
        sa.column("language", sa.String),
        sa.column("status", sa.String),
        sa.column("source", sa.String),
    )
    op.bulk_insert(
        safety_tips,
        [
            {
                "title": f"{hazard_title} — {phase.title()}",
                "content": content,
                "hazard_type": hazard_id,
                "phase": phase,
                "language": "en",
                "status": "published",
                "source": "AapdaSetu baseline safety guidance",
            }
            for hazard_id, hazard_title, phase, content in _TIPS
        ],
    )


def downgrade() -> None:
    """Remove only the baseline safety records inserted by this migration."""
    op.execute(
        sa.text(
            "DELETE FROM safety_tips "
            "WHERE source = 'AapdaSetu baseline safety guidance'"
        )
    )
