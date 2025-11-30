# Cloud Deployment Readiness & Private Cloud Strategy

## Executive Summary

**Current Status**: ✅ **Not yet ready for Public Cloud** - "Private Cloud" strategy selected.

**Decision**: Instead of migrating to Google Cloud Platform (GCP) immediately, we will upgrade the local environment to a High Availability (HA) cluster.

**New Architecture**:
- **Compute**: 2x Apple M1 Mac Minis (Primary + Replica)
- **Network**: Cloudflare Tunnel (Load Balanced/Failover)
- **Power**: Dedicated UPS Battery Backup
- **Connectivity**: 1Gbps Fiber (450 Mbps Upload)
- **Database**: MongoDB Atlas (Cloud) - Stateless compute, cloud data

## Why This Strategy Wins

1. **Cost Efficiency**: Cloud costs would be ~$142/month. A second Mac Mini (~$350) pays for itself in **2.5 months**.
2. **Performance**: Your residential upload speed (450 Mbps) exceeds standard cloud VPS bandwidth tiers.
3. **Reliability**: Adding a second node and UPS removes the "Single Point of Failure" risk.
4. **Zero Downtime**: You can restart one Mac (updates/deployments) while the other handles traffic.
5. **Disaster Recovery**: By keeping database in cloud (MongoDB Atlas), site-level disasters don't cause data loss.

## Deployment Thresholds

### ✅ Stay on Private Cloud (Mac Cluster) If:

1. **Traffic is below 20,000 users/day**
   - Two M1 chips combined provide massive throughput
   - Network bandwidth (450 Mbps upload) can handle thousands of concurrent text streams

2. **Hardware Utilization is Healthy**
   - Cluster CPU load < 70%
   - RAM usage < 12GB per node

3. **Budget is Priority**
   - You prefer CAPEX (One-time hardware purchase) over OPEX (Monthly cloud rent)

### 🚀 Migrate to Google Cloud When:

1. **Physical Limitations are Met**
   - Traffic exceeds 450 Mbps sustained upload bandwidth
   - Concurrent connections overwhelm the residential router's NAT table

2. **Global Latency Matters**
   - You need users in Europe/Asia to have <100ms latency (Cloud CDN/Edge required)

3. **Compliance/SLA**
   - Enterprise clients require SOC2 compliance or guaranteed 99.99% SLAs that residential ISPs cannot legally provide

## Cost Analysis: Private vs. Public

### Option A: Private Cloud Cluster (Selected)

**One-Time Investment (CAPEX)**:
- 2nd Mac Mini (Used M1, 16GB): ~$350
- UPS Battery Backup (1500VA): ~$150
- **Total CAPEX: ~$500**

**Monthly Operating Costs (OPEX)**:
- Electricity (2 Macs + Network): ~$10-15/mo
- MongoDB Atlas (M0/M2): $0-9/mo (start free, scale as needed)
- Cloudflare Zero Trust: $0/mo
- **Total OPEX: ~$15-24/mo**

**Pros**:
- ✅ **High Availability**: No downtime if one machine dies
- ✅ **Zero Downtime Deploys**: Update Node A while Node B serves traffic
- ✅ **Asset Ownership**: You own the hardware
- ✅ **Cost Savings**: ~$127/month vs GCP (~$1,500/year savings)
- ✅ **Stateless Architecture**: Database in cloud = fireproof data

**Cons**:
- ❌ **ISP Risk**: If a fiber line is cut outside your house, both nodes go offline
- ❌ **Disaster Risk**: Fire/Flood affects both nodes (but data is safe in cloud)
- ❌ **No Geographic Distribution**: All traffic routes through single location

### Option B: Multi-Region Distributed Private Cloud (Advanced)

**One-Time Investment (CAPEX)**:
- 2nd Mac Mini (US): ~$350 (already counted in Option A)
- Asia VPS (Hetzner/DigitalOcean): $0 (friend's server)
- Europe VPS (Hetzner/DigitalOcean): $0 (friend's server)
- **Total CAPEX: ~$500** (same as Option A)

**Monthly Operating Costs (OPEX)**:
- Electricity (2 Macs + Network): ~$10-15/mo
- MongoDB Atlas (M0/M2): $0-9/mo
- Cloudflare Zero Trust: $0/mo
- Asia VPS: $0-20/mo (if friend charges, or free)
- Europe VPS: $0-20/mo (if friend charges, or free)
- **Total OPEX: ~$15-64/mo** (depending on VPS costs)

**Architecture**:
```
┌─────────────────────────────────────────────────────────┐
│                    Cloudflare Edge                      │
│              (Geographic Load Balancing)                │
└───────┬───────────────┬───────────────┬────────────────┘
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  US Cluster  │ │ Asia Server  │ │Europe Server │
│ 2x Mac Mini  │ │  (Friend)    │ │  (Friend)    │
│  (Home)      │ │              │ │              │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │ MongoDB Atlas   │
              │  (Cloud - US)   │
              └─────────────────┘
```

**Pros**:
- ✅ **Global Low Latency**: Users in Asia/Europe get <100ms response times
- ✅ **Geographic Redundancy**: 3 sites instead of 1 (much better disaster recovery)
- ✅ **Still Cost-Effective**: $15-64/mo vs $115-142/mo for GCP
- ✅ **Stateless Architecture**: All nodes connect to cloud database
- ✅ **Cloudflare Smart Routing**: Automatically routes users to nearest region

**Cons**:
- ❌ **Operational Complexity**: Managing 3 locations instead of 1
- ❌ **Deployment Complexity**: Need to deploy to 3 locations (can automate)
- ❌ **Dependency on Friends**: Relies on friends maintaining their servers
- ❌ **Database Latency**: Asia/Europe nodes have higher latency to MongoDB Atlas (US)
- ❌ **Coordination Required**: Need to coordinate updates across 3 locations

**When to Use**:
- ✅ You have trusted friends/partners in Asia and Europe
- ✅ Global user base requires low latency
- ✅ You want geographic redundancy without cloud costs
- ✅ You're comfortable managing distributed infrastructure

**Database Latency Consideration**:
- US nodes: <10ms to MongoDB Atlas
- Asia nodes: ~150-200ms to MongoDB Atlas (US region)
- Europe nodes: ~80-120ms to MongoDB Atlas (US region)

**Solution**: Consider MongoDB Atlas Multi-Region or use read replicas in Asia/Europe regions if latency becomes an issue.

### Option C: Google Cloud Platform (Future State)

**Monthly Infrastructure Costs (Estimated)**:

#### Option 1: Cloud Run (Serverless - Recommended)
```
Backend (Cloud Run):
- CPU: 2 vCPU
- Memory: 4GB
- Requests: ~23,000/day
- Estimated: $30/month

Payload CMS (Cloud Run):
- CPU: 1 vCPU
- Memory: 2GB
- Estimated: $20/month

MongoDB Atlas:
- M5 cluster (2GB RAM, 10GB storage): ~$30/month
- OR M10 cluster (if data > 5GB): ~$57/month
- Start with M5, upgrade to M10 when needed

Redis (Memorystore):
- 1GB cache
- Estimated: $35/month

Cloud Run Domain Mapping:
- SSL termination & custom domains included (no extra cost)
- Load balancing handled natively by Cloud Run
- $0 (vs $18/mo for separate Load Balancer)

Total: ~$115-142/month (depending on MongoDB tier)
```

**Break-Even Analysis**:
- Staying on Private Cloud saves ~$127/month compared to GCP
- The $500 hardware investment is recouped in **~4 months**

**Pros**:
- ✅ Auto-scaling
- ✅ High availability (99.9%+ SLA)
- ✅ Geographic distribution
- ✅ Managed services
- ✅ No hardware maintenance
- ✅ Better for 20,000+ users/day or when you need 99.9%+ uptime

**Cons**:
- ❌ Higher cost (8-10x Private Cloud: $115-142 vs $15-24/month)
- ❌ More complex setup
- ❌ Vendor lock-in
- ❌ Learning curve

## Recommended Architecture: The "Home Data Center"

### Option 1: Single-Region Cluster (Current Plan)

We utilize **Cloudflare Tunnel** in "Replica Mode" to treat both Mac Minis as a single logical origin.

```mermaid
graph TD
    User[Public User] --> CF[Cloudflare Edge]
    CF -->|Tunnel| Mac1[Mac Mini A<br/>Primary]
    CF -->|Tunnel| Mac2[Mac Mini B<br/>Replica]
    
    subgraph "Home Network (Gigabit Fiber)"
        Mac1
        Mac2
        UPS[UPS Battery Backup] -.-> Mac1
        UPS -.-> Mac2
        Router[ISP Router]
    end
    
    Mac1 --> Atlas[MongoDB Atlas<br/>Cloud Database]
    Mac2 --> Atlas
    
    style Mac1 fill:#90EE90
    style Mac2 fill:#90EE90
    style Atlas fill:#87CEEB
    style CF fill:#FFD700
```

### Option 2: Multi-Region Distributed (Advanced)

If you have friends in Asia and Europe, you can expand to a global network:

```mermaid
graph TD
    UserUS[US User] --> CF[Cloudflare Edge]
    UserASIA[Asia User] --> CF
    UserEU[Europe User] --> CF
    
    CF -->|Geo-Route| US[US Cluster<br/>2x Mac Mini]
    CF -->|Geo-Route| ASIA[Asia Server<br/>Friend's VPS]
    CF -->|Geo-Route| EU[Europe Server<br/>Friend's VPS]
    
    US --> Atlas[MongoDB Atlas<br/>Cloud Database]
    ASIA --> Atlas
    EU --> Atlas
    
    style US fill:#90EE90
    style ASIA fill:#FFB6C1
    style EU fill:#87CEEB
    style Atlas fill:#FFD700
    style CF fill:#FFA500
```

### Implementation Details

**Single-Region Cluster**:
1. **Redundancy**: Both Macs run `cloudflared` with the **same tunnel token**
2. **Load Balancing**: Cloudflare automatically distributes requests to available nodes
3. **Failover**: If Mac A loses power or reboots, traffic shifts 100% to Mac B instantly
4. **Stateless Compute**: Both nodes connect to MongoDB Atlas (cloud) - no local database
5. **Zero Data Loss**: If house burns down, data survives in MongoDB Atlas

**Multi-Region Distributed**:
1. **Geographic Routing**: Cloudflare automatically routes users to nearest region based on IP
2. **Same Tunnel Token**: All 3 locations use the same Cloudflare Tunnel token (replica mode)
3. **Health Checks**: Cloudflare only routes to healthy regions
4. **Stateless Everywhere**: All nodes connect to MongoDB Atlas - no local state
5. **Deployment**: Deploy to all 3 regions simultaneously (can automate)
6. **Database Latency**: Asia/Europe nodes have higher latency to Atlas (US) - consider Atlas multi-region if needed

### The "Stateless Home Lab" Strategy

**Key Principle**: Treat Mac Minis as **ephemeral compute nodes**. No persistent data of value is stored on the physical machines.

**Data Persistence (The "Golden Copy")**:
- **Database**: MongoDB Atlas (Cloud) - NOT hosted locally
  - *Cost*: Start with M0 (Free) or M2 ($9/mo)
  - *Benefit*: If the house burns, your user data survives
- **Code**: All code committed to GitHub
- **Env Vars**: Encrypted copy stored in 1Password/Bitwarden
- **Assets**: Can be stored in S3/R2 or backed up nightly to cloud

## Disaster Recovery & Risk Mitigation

### The "Site Failure" Risk (Fire/Flood/Theft)

**Risk**: Since both nodes (Mac Minis) are in the same physical location, a site-level disaster destroys the entire cluster.

**Mitigation Strategy: Stateless Architecture**

By keeping the database in MongoDB Atlas (cloud), we ensure that **zero unique data lives on the Mac Minis**. This makes the setup "fireproof" from a data perspective.

### The "House Fire" Protocol

If the worst happens, your recovery plan is the **Google Cloud Deployment Playbook**.

1. **Event**: House is lost. Mac Minis are destroyed.
2. **Immediate Action**: Go to a coffee shop (or use your phone).
3. **Execution**: Run the `scripts/deploy-gcp.sh` script from your repo.
4. **Result**:
   - Google Cloud Run spins up (replacing the Mac Minis)
   - It connects to MongoDB Atlas (which is safe)
   - It pulls code from GitHub (which is safe)
   - **Outcome**: You are back online in **15-30 minutes** with **zero data loss**

### Revised Cost/Risk Profile

| Component | Location | Risk of Fire | Impact | Recovery Cost |
|-----------|----------|--------------|--------|---------------|
| **Compute** | Home (Mac Cluster) | **High** | Service Offline | ~$142/mo (Switch to GCP) |
| **Database** | **Cloud (Atlas)** | **Zero** | None | $0 (Already in cloud) |
| **Code** | GitHub | **Zero** | None | $0 |
| **Backups** | Cloud Storage | **Zero** | None | $0 |

**Verdict**: By moving *only* the Database to the cloud (MongoDB Atlas), you insulate yourself from catastrophic loss of the house while maintaining the $127/mo savings on compute.

**RTO (Recovery Time Objective)**: < 30 Minutes  
**RPO (Recovery Point Objective)**: < 1 Second (Zero data loss)

## Revised Migration Roadmap

### Phase 1: Hardware Acquisition (Immediate)

1. Purchase 2nd M1 Mac Mini (16GB RAM recommended)
2. Purchase UPS (Uninterruptible Power Supply) - Ensure Router & Modem are plugged in
3. Connect both units via Ethernet for stability

### Phase 2: Cluster Configuration (This Month)

1. **Sync Environment**: Ensure Node B has identical Docker/Env configuration to Node A
2. **Configure Cloudflare**: Install `cloudflared` on Node B using the existing token
3. **Database Migration**: Move MongoDB to Atlas (if not already there)
   - *Option A (Simpler)*: Both Nodes connect to MongoDB Atlas (Cloud) - **Recommended**
   - *Option B (Cheaper)*: Run Mongo on Node A, replica on Node B (Requires advanced config)
   - *Recommendation*: Stick with Atlas M0/M2 for now to keep state management simple
4. **Test Failover**: Unplug Node A ethernet and verify app stays online via Node B
5. **Verify Stateless**: Ensure both nodes can start fresh and connect to Atlas

### Phase 3: Operations & Drills

1. **Deployment Script**: Update deploy scripts to push to Node A, check health, then push to Node B
2. **Monitoring**: Set up Prometheus/Grafana to monitor *both* nodes on a single dashboard
3. **Disaster Recovery Drill**: Test the "House Fire" protocol by deploying to GCP from scratch

### Phase 3.5: Multi-Region Expansion (Optional - When Global Latency Matters)

**Prerequisites**:
- Trusted friends/partners in Asia and Europe willing to host
- US cluster is stable and operational
- You have deployment automation in place

**Setup Steps**:

1. **Asia Server Setup**:
   - Friend installs Docker and required dependencies
   - Clone repository from GitHub
   - Configure environment variables (connect to MongoDB Atlas)
   - Install `cloudflared` with same tunnel token as US cluster
   - Test connectivity to MongoDB Atlas

2. **Europe Server Setup**:
   - Same as Asia server setup
   - Ensure both servers are stateless (no local database)

3. **Cloudflare Configuration**:
   - Cloudflare automatically routes users to nearest region
   - All three locations use same tunnel token (replica mode)
   - Health checks ensure only healthy regions receive traffic

4. **Deployment Automation**:
   ```bash
   # Example: deploy-all-regions.sh
   ./deploy.sh us-cluster
   ./deploy.sh asia-server
   ./deploy.sh europe-server
   ```

5. **Monitoring**:
   - Add Asia and Europe servers to Prometheus/Grafana
   - Monitor latency from each region to MongoDB Atlas
   - Set up alerts for regional failures

**Benefits**:
- Global users get <100ms latency
- 3-site redundancy (much better than single location)
- Still cheaper than full cloud migration
- Maintains stateless architecture

**Challenges**:
- Need to coordinate deployments across 3 locations
- Database latency from Asia/Europe to Atlas (US) - consider multi-region Atlas
- Dependency on friends maintaining servers
- More complex troubleshooting

### Phase 4: Public Cloud (Future Trigger)

- **Trigger**: When 450 Mbps upload is saturated or compliance requirements demand it
- **Action**: Execute the [Google Cloud Deployment Playbook](./GOOGLE_CLOUD_DEPLOYMENT_PLAYBOOK.md)

## Decision Matrix: Revised

| Factor | Single Mac Mini | **Private Cloud Cluster** (Selected) | Multi-Region Private Cloud | Google Cloud |
|--------|----------------|----------------------------------------|----------------------------|-------------|
| **Setup Cost** | $0 | ~$500 (One-time) | ~$500 (One-time) | $0 |
| **Monthly Cost** | ~$5-10 | ~$15-24 | ~$15-64 | ~$115-142 |
| **Reliability** | Low (SPOF) | **High (HA)** | **Very High (3 sites)** | Very High (SLA) |
| **Max Capacity** | ~10k users | **~20k users** | **~60k users** (3x) | Unlimited |
| **Maintenance** | Manual | **Semi-Automated** | **Semi-Automated** | Managed |
| **Bandwidth** | 450 Mbps | **450 Mbps** | **1.35 Gbps** (3x) | Scalable |
| **Global Latency** | High (US only) | High (US only) | **Low (<100ms)** | Low (<100ms) |
| **Disaster Recovery** | None | **Stateless (Cloud DB)** | **3-Site Redundancy** | Built-in |
| **Zero Downtime Deploys** | ❌ | **✅** | **✅** | ✅ |
| **Data Safety** | Local only | **Cloud DB** | **Cloud DB** | Cloud DB |
| **Complexity** | Simple | Medium | **High** | High |

## Final Recommendation

**Build the Cluster.**

Your internet connection (symmetric fiber) is the "Unfair Advantage" that makes this possible. By adding redundancy (2nd Mac) and power protection (UPS), you eliminate the biggest risks of self-hosting while saving ~$1,500/year in cloud fees.

The **stateless architecture** (compute at home, data in cloud) provides the best of both worlds:
- **Cost savings** of self-hosted compute
- **Data safety** of cloud-hosted database
- **Disaster recovery** via the GCP playbook

### Evolution Path

**Phase 1** (Now): Build single-region cluster (2x Mac Minis in US)
- Handles up to 20,000 users/day
- Cost: ~$15-24/month
- Perfect for US-focused traffic

**Phase 2** (When Global): Add Asia/Europe servers (if you have trusted partners)
- Handles up to 60,000 users/day globally
- Cost: ~$15-64/month (still 1/3 the cost of GCP)
- Provides <100ms latency worldwide
- 3-site geographic redundancy

**Phase 3** (If Needed): Migrate to GCP
- Only if you need compliance/SLA guarantees
- Or if traffic exceeds 60,000 users/day
- Or if managing distributed infrastructure becomes too complex

## Migration Readiness Checklist

### Technical Readiness

- [x] All services containerized (✅ Done - Docker)
- [x] Environment variables documented (✅ Done)
- [x] Health checks implemented (✅ Done)
- [x] Monitoring in place (✅ Done - Prometheus/Grafana)
- [x] Logging configured (✅ Done)
- [ ] **Database migrated to Atlas** (Required for stateless architecture)
- [ ] **2nd Mac Mini acquired and configured**
- [ ] **UPS installed and tested**
- [ ] **Cloudflare Tunnel configured for both nodes**
- [ ] Backup/restore procedures (Need to document)
- [ ] CI/CD pipeline (Optional but recommended)

### Operational Readiness

- [ ] Team trained on cluster operations
- [ ] Cost monitoring/alerts configured
- [ ] Security best practices implemented
- [x] Disaster recovery plan (✅ GCP Playbook)
- [ ] Rollback procedures documented
- [ ] Support plan (who handles issues?)

### Business Readiness

- [x] Budget approved for hardware ($500 one-time)
- [x] Growth projections justify cluster setup
- [ ] Uptime requirements defined
- [ ] Migration timeline planned

## Cost Comparison at Different Scales

| Users/Day | Single Mac | Private Cluster | Multi-Region Private | GCP Cost (Cloud Run) | Best Option |
|-----------|------------|-----------------|----------------------|---------------------|-------------|
| 500 | $5-10 | $15-24 | $15-64 | $50-80 | 🏆 Single Mac |
| 2,000 | $5-10 | $15-24 | $15-64 | $80-120 | 🏆 Private Cluster |
| 5,000 | $5-10 | $15-24 | $15-64 | $115-150 | 🏆 Private Cluster |
| 10,000 | $5-10 | $15-24 | $15-64 | $180-220 | 🏆 Private Cluster |
| 20,000 | ❌ Hardware limit | $15-24 | $15-64 | $300-400 | 🏆 Private Cluster |
| 50,000+ | ❌ | ❌ Bandwidth limit | $15-64 | $400-600 | 🏆 Multi-Region |
| Global Users | ❌ | ❌ High Latency | $15-64 | $400-600 | 🏆 Multi-Region |

**Break-even point**: 
- Private Cloud Cluster pays for itself in ~4 months vs GCP
- Multi-Region Private Cloud handles global traffic at 1/3 the cost of GCP
- Single-region cluster handles up to 20,000 users/day
- Multi-region cluster handles up to 60,000 users/day (3x capacity)

## Multi-Region Considerations

### When Multi-Region Makes Sense

✅ **Use Multi-Region If**:
- You have significant user base in Asia/Europe (>20% of traffic)
- You have trusted friends/partners willing to host
- Global latency is a competitive advantage
- You want geographic redundancy without cloud costs
- You're comfortable managing distributed infrastructure

❌ **Stick with Single-Region If**:
- 90%+ of users are in US
- You don't have trusted partners in other regions
- Operational complexity is a concern
- You prefer simplicity over global reach

### Database Latency Optimization

**Challenge**: Asia/Europe servers connecting to MongoDB Atlas (US region) have higher latency:
- US → Atlas: <10ms
- Asia → Atlas: ~150-200ms
- Europe → Atlas: ~80-120ms

**Solutions**:

1. **MongoDB Atlas Multi-Region** (Recommended for high traffic):
   - Deploy Atlas clusters in US, Asia, and Europe
   - Automatic replication between regions
   - Read from nearest region, write to primary
   - Cost: ~$90-150/month (3x M5 clusters)

2. **Read Replicas** (Cost-effective):
   - Primary Atlas cluster in US
   - Read replicas in Asia/Europe regions
   - Writes go to US, reads from nearest region
   - Cost: ~$60-90/month (1 primary + 2 replicas)

3. **Accept Higher Write Latency** (Simplest):
   - All nodes write to US Atlas
   - Accept 150-200ms write latency from Asia
   - Most reads can be cached locally
   - Cost: ~$30-57/month (single M5/M10 cluster)

**Recommendation**: Start with Option 3 (single Atlas cluster). If write latency becomes an issue, upgrade to Option 2 (read replicas).

### Deployment Strategy

**Option A: Sequential Deployment** (Safer):
```bash
# Deploy to US first, verify, then expand
./deploy.sh us-cluster
# Wait for health check
./deploy.sh asia-server
./deploy.sh europe-server
```

**Option B: Parallel Deployment** (Faster):
```bash
# Deploy to all regions simultaneously
./deploy-all-regions.sh
```

**Option C: Blue-Green by Region** (Zero Downtime):
```bash
# Deploy new version to staging, then switch regions one by one
./deploy.sh us-cluster --blue-green
./deploy.sh asia-server --blue-green
./deploy.sh europe-server --blue-green
```

**Recommendation**: Start with Option A (sequential) for safety. Once confident, move to Option B (parallel) for speed.

## Next Steps

1. **Immediate**: Purchase 2nd Mac Mini and UPS
2. **This Week**: Set up MongoDB Atlas (if not already done)
3. **This Month**: Configure cluster with Cloudflare Tunnel
4. **Short-term** (1-3 months): Test failover, run disaster recovery drill
5. **Medium-term** (3-6 months): Monitor cluster performance, reassess based on traffic growth
6. **When Ready**: Execute production migration to GCP using playbook (traffic > 20,000 users/day or bandwidth saturated)

## Recommended Action Plan

### ✅ Do Now (This Week)
1. **Purchase hardware** - 2nd Mac Mini + UPS
2. **Set up MongoDB Atlas** - Migrate database to cloud (if not already done)
3. **Document current setup** - Full documentation of Mac Mini deployment

### ⚠️ Prepare (This Month)
1. **Configure cluster** - Set up Node B with identical environment
2. **Configure Cloudflare** - Set up tunnel on both nodes
3. **Test failover** - Verify traffic shifts between nodes
4. **Update monitoring** - Add Node B to Prometheus/Grafana dashboard

### 🚀 Execute (When Hardware Arrives)
1. **Hardware setup** - Install UPS, connect both Macs via Ethernet
2. **Cluster deployment** - Deploy services to both nodes
3. **Load testing** - Verify cluster handles traffic correctly
4. **Disaster drill** - Test GCP deployment from scratch

## References

- [Google Cloud Deployment Playbook](./GOOGLE_CLOUD_DEPLOYMENT_PLAYBOOK.md) - Your disaster recovery plan
- [Capacity Planning Guide](./CAPACITY_PLANNING.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Environment Variables](./ENVIRONMENT_VARIABLES.md)
- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [MongoDB Atlas Pricing](https://www.mongodb.com/pricing)
