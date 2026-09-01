"""
Seed data for Knowledge Park 3, Greater Noida — Realistic Urban Flood Scenario.
Inserts Knowledge Park 3 zones, resources, hospitals, road blocks, and citizen reports.
"""
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

async def seed_kp3_database(db: AsyncIOMotorDatabase):
    print("[Seed KP3] Seeding Knowledge Park 3, Greater Noida data...")
    now = datetime.now(timezone.utc)

    # ── 1. ZONES (Knowledge Park 3 & surrounding critical junctions) ──
    zones = [
        {
            "zone_id": "zone-kp3-north",
            "ward_name": "KP3 Institutional Belt (Sharda & Galgotias)",
            "risk_level": "critical",
            "depth_meters": 0.65,
            "population_affected": 24000,
            "evacuation_shelter": "Galgotias Campus Hall B",
            "critical_infra": ["Sharda University", "Galgotias College", "Substation KP3"],
            "lat": 28.4735,
            "lng": 77.4980,
            "last_assessed": now - timedelta(minutes=5),
            "deleted_at": None,
        },
        {
            "zone_id": "zone-pari-chowk",
            "ward_name": "Pari Chowk Roundabout & Underpass",
            "risk_level": "critical",
            "depth_meters": 0.82,
            "population_affected": 35000,
            "evacuation_shelter": "Alpha-1 Community Centre",
            "critical_infra": ["Pari Chowk Metro Station", "Noida Expressway Junction"],
            "lat": 28.4650,
            "lng": 77.5090,
            "last_assessed": now - timedelta(minutes=3),
            "deleted_at": None,
        },
        {
            "zone_id": "zone-sharda-rotary",
            "ward_name": "Sharda Hospital & Medical Corridor",
            "risk_level": "medium",
            "depth_meters": 0.35,
            "population_affected": 18000,
            "evacuation_shelter": "GIMS Auditorium",
            "critical_infra": ["Sharda Hospital Trauma Center", "Blood Bank"],
            "lat": 28.4770,
            "lng": 77.4920,
            "last_assessed": now - timedelta(minutes=8),
            "deleted_at": None,
        },
        {
            "zone_id": "zone-kp3-metro",
            "ward_name": "Knowledge Park II / KP III Metro Link",
            "risk_level": "high",
            "depth_meters": 0.52,
            "population_affected": 28000,
            "evacuation_shelter": "Greater Noida Stadium Pavilion",
            "critical_infra": ["KP II Aqua Line Metro", "Main Feeder Substation"],
            "lat": 28.4680,
            "lng": 77.4950,
            "last_assessed": now - timedelta(minutes=10),
            "deleted_at": None,
        },
        {
            "zone_id": "zone-gl-bajaj",
            "ward_name": "GL Bajaj & Accurate Academic Sector",
            "risk_level": "low",
            "depth_meters": 0.18,
            "population_affected": 12000,
            "evacuation_shelter": "Accurate Institute Indoor Sports Complex",
            "critical_infra": ["Hostel Complexes", "Local Commercial Plazas"],
            "lat": 28.4610,
            "lng": 77.4930,
            "last_assessed": now - timedelta(minutes=12),
            "deleted_at": None,
        },
    ]
    for z in zones:
        await db.zones_kp3.update_one({"zone_id": z["zone_id"]}, {"$set": z}, upsert=True)

    # ── 2. HOSPITALS (Real Greater Noida & KP3 Medical Centers) ──
    hospitals = [
        {
            "hospital_id": "hosp-sharda",
            "hospital_name": "Sharda Hospital & Trauma Center",
            "zone_id": "zone-sharda-rotary",
            "general_beds_available": 65,
            "general_beds_total": 350,
            "icu_beds_available": 12,
            "icu_beds_total": 40,
            "emergency_beds_available": 18,
            "emergency_beds_total": 60,
            "ambulances_available": 6,
            "ambulances_total": 10,
            "blood_o_positive": 45,
            "iv_fluids_bags": 500,
            "tetanus_doses": 300,
            "last_updated": now,
            "deleted_at": None,
        },
        {
            "hospital_id": "hosp-kailash",
            "hospital_name": "Kailash Hospital Greater Noida",
            "zone_id": "zone-pari-chowk",
            "general_beds_available": 40,
            "general_beds_total": 200,
            "icu_beds_available": 8,
            "icu_beds_total": 25,
            "emergency_beds_available": 10,
            "emergency_beds_total": 30,
            "ambulances_available": 4,
            "ambulances_total": 6,
            "blood_o_positive": 30,
            "iv_fluids_bags": 350,
            "tetanus_doses": 200,
            "last_updated": now,
            "deleted_at": None,
        },
        {
            "hospital_id": "hosp-yatharth",
            "hospital_name": "Yatharth Super Speciality Hospital",
            "zone_id": "zone-kp3-metro",
            "general_beds_available": 80,
            "general_beds_total": 400,
            "icu_beds_available": 15,
            "icu_beds_total": 50,
            "emergency_beds_available": 22,
            "emergency_beds_total": 70,
            "ambulances_available": 8,
            "ambulances_total": 12,
            "blood_o_positive": 60,
            "iv_fluids_bags": 600,
            "tetanus_doses": 400,
            "last_updated": now,
            "deleted_at": None,
        },
    ]
    for h in hospitals:
        await db.hospital_capacity_kp3.update_one({"hospital_id": h["hospital_id"]}, {"$set": h}, upsert=True)

    # ── 3. RESOURCES ──
    resources = [
        {"resource_id": "PUMP-KP3-01", "resource_type": "pump", "name": "Heavy Duty 25HP Dewatering Pump", "capacity": 1, "status": "deployed", "current_zone_id": "zone-pari-chowk", "owner_role": "government", "home_station": "GNIDA Depot Pari Chowk", "lat": 28.4650, "lng": 77.5090, "last_updated": now, "deleted_at": None},
        {"resource_id": "PUMP-KP3-02", "resource_type": "pump", "name": "Submersible Drainage Pump 10HP", "capacity": 1, "status": "available", "current_zone_id": None, "owner_role": "government", "home_station": "Knowledge Park 3 Maintenance Office", "lat": 28.4720, "lng": 77.4980, "last_updated": now, "deleted_at": None},
        {"resource_id": "AMB-KP3-01", "resource_type": "ambulance", "name": "108 Advanced Life Support Unit 1", "capacity": 2, "status": "available", "current_zone_id": None, "owner_role": "hospital", "home_station": "Sharda Hospital", "lat": 28.4770, "lng": 77.4920, "last_updated": now, "deleted_at": None},
        {"resource_id": "AMB-KP3-02", "resource_type": "ambulance", "name": "108 Emergency Ambulance Unit 2", "capacity": 2, "status": "deployed", "current_zone_id": "zone-kp3-north", "owner_role": "hospital", "home_station": "Yatharth Hospital", "lat": 28.4735, "lng": 77.4980, "last_updated": now, "deleted_at": None},
        {"resource_id": "SDRF-KP3-01", "resource_type": "rescue_vehicle", "name": "UP SDRF Flood Rescue Team 1", "capacity": 10, "status": "available", "current_zone_id": None, "owner_role": "government", "home_station": "Surajpur Emergency Base", "lat": 28.4700, "lng": 77.5000, "last_updated": now, "deleted_at": None},
        {"resource_id": "FIRE-KP3-01", "resource_type": "fire_engine", "name": "Water Tender Heavy Unit Alpha", "capacity": 6, "status": "available", "current_zone_id": None, "owner_role": "fire", "home_station": "Surajpur Fire Station", "lat": 28.4680, "lng": 77.5050, "last_updated": now, "deleted_at": None},
    ]
    for r in resources:
        await db.resources_kp3.update_one({"resource_id": r["resource_id"]}, {"$set": r}, upsert=True)

    print("  [OK] Seeded 5 Zones, 3 Hospitals, 6 Resources for Knowledge Park 3.")
