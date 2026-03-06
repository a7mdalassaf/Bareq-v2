# Bareq v2 — Deployment & Development Plan

## Phase 1: Energy Monitoring Foundation (Week 1-2)

### Step 1: Extend Tuya Integration for Power Monitoring ✅
- [ ] Update `tuya_adapter.py` to fetch power consumption data
- [ ] Add methods: `get_device_power()`, `get_power_history()`
- [ ] Test with smart plugs/breakers that support power monitoring
- [ ] Document Tuya power monitoring API endpoints

### Step 2: Create Energy Data Models
- [ ] Add `EnergyReading` model (timestamp, device_id, watts, kwh)
- [ ] Add `ApartmentConsumption` model (apartment_id, daily/monthly totals)
- [ ] Add `BuildingStats` model (aggregate consumption, cost analysis)
- [ ] Create database migrations

### Step 3: Build Consumption Tracking Backend
- [ ] Add background job to poll Tuya devices for power data
- [ ] Store readings in database (configurable intervals: 5/15/30 min)
- [ ] Add API endpoints:
  - `GET /api/energy/current` — Real-time consumption
  - `GET /api/energy/history` — Historical data (daily/weekly/monthly)
  - `GET /api/energy/apartments` — Per-apartment breakdown
  - `GET /api/energy/anomalies` — Detect unusual patterns

### Step 4: Build Energy Dashboard UI
- [ ] Create `/dashboard` route (authenticated)
- [ ] Real-time consumption widget (current kWh, cost estimate)
- [ ] Historical charts (Chart.js or similar)
- [ ] Apartment comparison table
- [ ] Peak load timeline
- [ ] Anomaly alerts section

---

## Phase 2: Analytics & Alerts (Week 3-4)

### Step 5: Peak Load Detection
- [ ] Analyze historical data to identify peak usage windows
- [ ] Add configurable thresholds per apartment/building
- [ ] Alert when peak exceeded
- [ ] Recommendations for load balancing

### Step 6: Anomaly Detection
- [ ] Baseline calculation (average consumption patterns)
- [ ] Spike detection (sudden increases >30%)
- [ ] Sustained high usage alerts (prolonged above baseline)
- [ ] Notify operators via email/SMS (optional)

### Step 7: Cost Analysis
- [ ] Add configurable energy rates (kWh pricing)
- [ ] Calculate daily/monthly costs per apartment
- [ ] Generate billing-ready reports
- [ ] Export to CSV/PDF

---

## Phase 3: Multi-Building & Production Deploy (Week 5-6)

### Step 8: Multi-Building Support
- [ ] Add `Building` model (name, address, config)
- [ ] Associate apartments/devices with buildings
- [ ] Portfolio-wide dashboard
- [ ] Comparative analytics across buildings

### Step 9: Production Deployment
- [ ] Deploy to DigitalOcean droplet (bareq-housing-1 or new)
- [ ] Configure Nginx to proxy `/dashboard` → Flask app
- [ ] Set up SSL (Let's Encrypt)
- [ ] Configure systemd service
- [ ] Set up monitoring (uptime, logs)

### Step 10: Security & Access Control
- [ ] Implement proper authentication (Flask-Login or JWT)
- [ ] Role-based access (admin, building manager, resident)
- [ ] Audit logging for all actions
- [ ] Rate limiting on API endpoints

---

## Current Status

### ✅ Completed
- Created Bareq-v2 repository
- Merged Smarta-v0.5 foundation
- Updated README and project documentation
- Pushed initial commit

### 🔄 In Progress
- None (awaiting Phase 1 kick-off)

### 📋 Next Actions
1. Extend Tuya adapter for power monitoring
2. Create energy data models
3. Build consumption tracking backend

---

## Deployment Configuration

### Server Details
- **Current:** bareq-1 droplet @ 206.189.110.53 (running Smarta backend)
- **Nginx config:** `/etc/nginx/sites-enabled/bareq`
- **Service:** `/etc/systemd/system/bareq.service`

### Transition Plan
Option A: Deploy Bareq v2 to same server (update existing deployment)
Option B: New droplet for Bareq v2, keep Smarta separate

**Recommendation:** Option A (update in place, keep backward compatibility)

---

## Questions to Resolve

1. **Tuya devices:** Do current smart plugs/breakers support power monitoring? (Need device IDs to test)
2. **Authentication:** Keep simple session-based or use JWT for API?
3. **Data retention:** How long to keep historical readings? (30/90/365 days?)
4. **Alerts:** Email only or add SMS/push notifications?

---

Last updated: 2026-03-07
