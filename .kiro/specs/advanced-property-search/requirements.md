# Requirements Document

## Introduction

The Advanced Property Search platform is a web application that enables home buyers and renters to search for properties using sophisticated filters that go beyond basic criteria offered by existing platforms like Rightmove and Zoopla. The system will integrate multiple data sources including property listings, geographic data, environmental data, and transportation information to provide users with a comprehensive search experience based on lifestyle and quality-of-life factors.

In the MVP, we want to implement an intelligent, natural‑language–driven, multi‑constraint search that translates free‑form queries into structured criteria, applies a transparent multi‑objective ranking engine (e.g., price, size, commute time, amenity proximity, environmental quality, financial value proposition) with user‑adjustable weights, and visualises results on an interactive, layerable map. Data pipelines will emphasise provenance and freshness (lineage stamps and staleness flags) with graceful degradation when third‑party feeds are unavailable, and each result will include an explainable “why this home?” breakdown to build user trust and enable rapid iteration.

The buyers of today are far more conscious of environmental and health related factors. Their wants and needs are more diverse, they need a property search platform that can leverage AI to narrow down their search and provide a better match for preferences. They don't need a list of 1000s properties within 20 miles, they need a list of the top 10 matches that meet all of their preferences. We want to aggregate mutliple data-sources into a singular page displayed in a digestable format to allow consumers to make informed decisions.

## Requirements

### Requirement 1

**User Story:** As a property searcher, I want to search for properties using complex lifestyle-based filters, so that I can find homes that match my specific quality-of-life requirements.

#### Acceptance Criteria

1. WHEN a user enters search criteria THEN the system SHALL accept filters for proximity to parks, green spaces, train stations, gyms, and other amenities
2. WHEN a user specifies distance requirements THEN the system SHALL support both straight-line distance and walking distance calculations
3. WHEN a user wants to avoid certain areas THEN the system SHALL accept filters for avoiding noise sources like airports and high pollution areas using data aggregated from multiple sources including property listings, map data, pollution data, and transportation data
5. IF a user specifies conflicting filters THEN the system SHALL provide clear feedback about the conflicts

### Requirement 2

**User Story:** As a property searcher, I want to see search results displayed on an interactive map, so that I can visualize property locations in relation to my filter criteria.

#### Acceptance Criteria

1. WHEN search results are returned THEN the system SHALL display properties as markers on an interactive map
2. WHEN a user clicks on a property marker THEN the system SHALL display property details including how it meets the specified filter criteria
3. WHEN displaying results THEN the system SHALL show relevant contextual information like nearby amenities, transport links, and environmental factors, proximity to nearby relatives' houses, each represented as an alternative layer in the map with the filters displayed using a colour coding scheme
4. WHEN a user zooms or pans the map THEN the system SHALL maintain filter context and update results accordingly

### Requirement 3

**User Story:** As a property searcher, I want to use a simple search interface with intelligent suggestions (taking inspiration from apples spotlight feature), so that I can easily discover and utilize the platform's advanced filtering capabilities.

#### Acceptance Criteria

1. WHEN a user accesses the platform THEN the system SHALL present a clean interface with a single search bar and map
2. WHEN a user types in the search bar THEN the system SHALL provide intelligent suggestions that demonstrate available filter capabilities
3. WHEN suggestions are displayed THEN the system SHALL include examples like "within 10 minutes walk of a train station" or "near parks and green spaces"
4. WHEN a user selects a suggestion THEN the system SHALL automatically configure the appropriate filters
5. IF a user enters free-form text THEN the system SHALL attempt to parse and convert it into structured filter criteria

### Requirement 4

**User Story:** As a property searcher, I want the system to integrate with existing property listing platforms, so that I can access comprehensive and up-to-date property data.

#### Acceptance Criteria

1. WHEN the system searches for properties THEN it SHALL retrieve listings from Rightmove and Zoopla APIs or data sources
2. WHEN property data is retrieved THEN the system SHALL normalize and standardize the data format across different sources
3. WHEN displaying property information THEN the system SHALL include standard details like price, bedrooms, bathrooms, and property type
4. WHEN property data is outdated THEN the system SHALL refresh listings within a reasonable timeframe
5. IF a property listing source is unavailable THEN the system SHALL continue to function with available data sources

### Requirement 5

**User Story:** As a property searcher, I want the system to provide accurate environmental and transportation data, so that I can make informed decisions about property locations.

#### Acceptance Criteria

1. WHEN calculating distances to amenities THEN the system SHALL use accurate geographic data and routing information
2. WHEN displaying pollution information THEN the system SHALL integrate current air quality and noise pollution data
3. WHEN showing transportation options THEN the system SHALL include real-time or scheduled public transport information
4. WHEN identifying green spaces THEN the system SHALL use up-to-date mapping data to locate parks, forests, and recreational areas
5. IF environmental data is unavailable for an area THEN the system SHALL clearly indicate data limitations to the user

### Requirement 6

**User Story:** As a property searcher, I want the system to be responsive and performant, so that I can efficiently search and browse properties without delays.

#### Acceptance Criteria

1. WHEN a user performs a search THEN the system SHALL return initial results within 3 seconds
2. WHEN loading map data THEN the system SHALL display properties progressively as data becomes available
3. WHEN applying multiple complex filters THEN the system SHALL maintain responsive performance
4. WHEN handling large result sets THEN the system SHALL implement pagination or clustering to maintain performance
5. IF the system experiences high load THEN it SHALL gracefully handle requests without timing out

### Requirement 7

**User Story:** As a property searcher, I want to save and manage my search criteria and favorite properties, so that I can track my property search progress over time, sharing search results and filters should be a first-class feature.

#### Acceptance Criteria

1. WHEN a user creates a useful search THEN the system SHALL allow saving the search criteria for future use
2. WHEN a user finds interesting properties THEN the system SHALL allow marking properties as favorites
3. WHEN a user returns to the platform THEN the system SHALL provide access to saved searches and favorite properties
4. WHEN saved searches have new matching properties THEN the system SHALL optionally notify the user
5. IF a user wants to modify saved searches THEN the system SHALL allow editing and updating search criteria

### Requirement 8

**User Story:** As a property searcher with multi‑stop daily routines, I want to constrain and rank homes by door‑to‑door travel times across multiple destinations (e.g., nursery → work → gym) with peak/off‑peak awareness and preferred transport modes, so that search results reflect my real‑world lifestyle.

#### Acceptance Criteria

1. WHEN a user configures a Commute Profile THEN the system SHALL allow adding 2–5 destinations with labels (e.g., “Nursery”, “Work”, “Gym”), selecting preferred modes (walking, cycling, public transport, driving), defining peak/off‑peak windows and active weekdays, and adjusting sliders for max detour per stop and max per‑leg / total chain time.
2. WHEN the system computes commute times for a property THEN it SHALL calculate door‑to‑door durations including access (walk/drive/park), wait/interchange times from timetables, in‑vehicle time, and egress to the destination; AND it SHALL support AM (property → … → last stop) and PM (reverse) chains, providing median and p95 estimates for each leg and the total chain.
3. WHEN a user applies a Commute Profile to a search THEN the system SHALL filter properties that meet required thresholds (per‑leg and total) and SHALL score properties that meet preferred thresholds using user‑adjustable weights for commute; AND the ranking.
4. WHEN a property or search area is displayed on the map THEN the system SHALL render isochrones per destination (distinct colours, legend) and a chained‑route preview with per‑leg tooltips.
5. WHEN commute constraints are mutually exclusive or yield no results THEN the system SHALL display a clear notice identifying which constraints failed and SHALL offer actionable relaxations (e.g., extend total chain by 5–10 minutes, relax a specific leg, broaden peak window, switch/allow an additional mode).
6. WHEN a user saves a search THEN the associated Commute Profile (destinations, modes, thresholds, windows, weights) SHALL be persisted; AND WHEN a user shares a search link THEN recipients who open it SHALL see the same commute constraints applied (with destination precision reduced to street/postcode unless the sender opts to share exact points).
7. WHEN presenting commute results THEN the system SHALL provide a textual breakdown (screen‑reader friendly) of each leg and total chain and SHALL be fully keyboard navigable for configuring and applying the Commute Profile.
11. WHEN validating routing accuracy THEN the system SHALL maintain a median absolute error within ±10% or ±5 minutes (whichever is greater) against sampled ground‑truth journeys per mode/window and SHALL include automated tests for chaining logic, timetable fallbacks, and edge cases (e.g., last train, station closures).

### Requirement 9

**User Story:** As a property searcher, I want transparent multi‑objective ranking with explainable results and adjustable preference weights, so that I can understand and control how my lifestyle priorities affect the results.

#### Acceptance Criteria

1. WHEN results are displayed THEN each property card/details view SHALL include a concise "Why this property?" explanation summarising how it meets the user’s criteria, with a per‑criterion score breakdown (e.g., price fit, commute, amenities, environmental factors, property features).
2. WHEN a user adjusts preference weights across objective categories (e.g., price, commute time, amenity proximity, environmental quality, property features) THEN the ranking SHALL update within 1 second for up to 500 results and within 2 seconds for larger result sets.
3. WHEN constraints are mutually exclusive or yield few/no results THEN the system SHALL display a conflict/exhaustion notice and offer actionable relaxations (e.g., increase budget by 5–10%, expand radius by 0.5–1 km, relax commute by 5–10 minutes).
4. WHEN data used in scoring is stale or unavailable THEN the system SHALL surface a staleness/missing‑data badge at both search and property levels, including last‑refreshed timestamps per data source.
5. WHEN a user saves a search THEN the system SHALL persist the weight profile with the search and allow sharing; recipients who open the shared link SHALL see the same criteria and weights applied.
6. WHEN a user inspects a score component THEN the system SHALL display the underlying metric (e.g., "12 min walk to [Station]; AQI 24 (Good); 250 m to [Park]") in an info panel, with source attribution available.

### Requirement 10

**User Story:** As a buyer or investor (and, where relevant, a long‑term renter), I want a single Financial Index Score (FIS) per property that summarises its value proposition, and an expandable Financials card that shows transparent, configurable metrics and assumptions, so that I can quickly compare options and make informed, long‑term decisions.

#### Acceptance Criteria

1. WHEN search results are displayed THEN the system SHALL show, on each property card (and on map pins where space allows), a Financial Index Score (FIS) from 0–100 with an A–E band and tooltip; AND WHEN a user clicks the FIS badge or a visible Financials affordance THEN the system SHALL open an in‑place Financials card (drawer or modal) without page navigation.
2. WHEN a user opens the Financials card for a for‑sale listing THEN the system SHALL display at minimum: (a) Value vs Area (price per m²/ft²; local median/percentiles; 3–5 nearby comparables with date/size/PPSF); (b) Price History & Liquidity (listing price changes; time‑on‑market vs area benchmark; 24‑month PPSF volatility); (c) Mortgage & Purchase Costs (configurable mortgage estimate, SDLT, legal/valuation/agent fees, upfront cash); (d) Running Costs (council tax band & cost; service charge & ground rent if leasehold; buildings insurance estimate; EPC‑informed energy cost range); (e) Yield (Investor View) (market rent range, gross and net yield after assumed costs, rent/bedroom, vacancy assumption); and (f) Risk Signals (flood‑risk category; lease length & flagged thresholds; optional area crime‑rate index; days‑to‑sell distribution).
3. WHEN a user opens the Financials card for a rental listing THEN the system SHALL display at minimum: (a) Affordability (rent‑to‑income ratio vs local median; projected annual rent; deposit & fees estimate); (b) Running Costs (council tax; EPC‑informed utilities; broadband availability/speed tier); and (c) Stability & Risk (area rent trend over 12–24 months; tenancy type indicators if available; time‑to‑let benchmarks).
4. WHEN a user opens the Financials card THEN the system SHALL display a “How this score is calculated” panel showing sub‑scores, weights, and a formula overview with each sub‑score’s contribution to the FIS; AND WHEN any metric is shown THEN the system SHALL include source attribution and last‑refreshed timestamps and SHALL visibly badge missing or stale data.
5. WHEN a user adjusts assumptions (including interest rate, term, LTV, holding period, voids, service charge, insurance, expected rent) THEN the system SHALL recompute the FIS and all dependent metrics and SHALL update the Financials card immediately; AND WHEN defaults are requested THEN the system SHALL restore defaults and SHALL allow saving/sharing of the active assumptions with the user profile.
