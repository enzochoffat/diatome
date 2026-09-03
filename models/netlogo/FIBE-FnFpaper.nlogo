;;; @author Nanda Wijermans
;;; @email nanda.wijermans@su.se
;;; @version 1.0

extensions [array csv]

__includes["init.nls" "utils.nls"]

breed [fishers fisher]

globals [
  end-of-sim
  number-of-fishers
  fishingAtA fishingAtB fishingAtC fishingAtD
  MAXXABC MAXXD MAXYA MAXYB MAXYCD  ; max coordinates of each region
  MINXABC MINXD MINYA MINYB MINYCD  ; min coordinates of each region

  LOW MEDIUM HIGH MEDIUM-HIGH  LOW-MEDIUM ; constants used to indicate levels
  LOW-COST-EXISTANCE MEDIUM-COST-EXISTANCE HIGH-COST-EXISTANCE ; different costs for a fisher (firm) to exist
  LOW-COST-ACTIVITY  MEDIUM-COST-ACTIVITY  HIGH-COST-ACTIVITY  ; different cost connected to go fishing, e.g. hiring people, time spend on the job - wage, etc   ;TODO is this still used
  LOW-COST-TRAVEL MEDIUM-COST-TRAVEL MEDIUM-COST-TRAVEL-BIGVESSEL HIGH-COST-TRAVEL ; different costs for traveling to the different regions
  cost-travelB2C cost-travelB2D cost-travelC2D                 ; cost when travelling from one region to the other
  CARRYING-CAPACITY LOW-CARCAP MEDIUM-CARCAP HIGH-CARCAP       ; carrrying capacity of the fish stock at a patch.

  ;constants and variables for the MSY benchmark
  CARCAP-A CARCAP-B CARCAP-C CARCAP-D
  CATCHABIL-AR CATCHABIL-CO CATCHABIL-TR ; constants use to indicate the different gear-based catch-abilities for the fishing styles archipelago (AR), coastal (CO) and offshore trawlers (TR)

  MSY-STOCK-A MSY-STOCK-B MSY-STOCK-C MSY-STOCK-D              ;optimal stock in the baseline scenario - optimal management
  opt-catch-A opt-catch-B opt-catch-C opt-catch-D              ;catch in the baseline scenario - optimal management
  opt-timeOut-A opt-timeOut-B opt-timeOut-C opt-timeOut-D      ;optimal time out for all fishers in a years time

  IS-A-CROWD            ; minumum number of fishers that is consdired a group - i.e. to be able to have effect on going where 'most' fisher go
  A B C D NULL          ; region labels for the patches indicating the type of sea and cod stock that is targeted when fisher fish there
  WEEK MONTH MONTH-IN-DAYS SEASON HALFYEAR YEAR ; constant for the number of tick for a week, month and season

  regionA regionB regionC regionD land ; agentset of the patches belonging to each region
  archipelagos coastals trawlers  ; agentset of the agents belonging to each fisher type
  hotspots hotspotCentresA hotspotCentresB hotspotCentresC hotspotCentresD ; patchset of hotspot centres
  medHighDensSpotsA medHighDensSpotsB medHighDensSpotsC medHighDensSpotsD ;patchset of the medium and high dense patches
  lowDensSpotsA lowDensSpotsB lowDensSpotsC lowDensSpotsD ; ;patchset of the low dense patches

  badWeather            ; boolean to indicate it is bad weather (archipelago and coastal cannot go out)

  hotSpotsVisible       ; variable that avoids unnecesary updating the layout
  fishDensVisible       ; variable that avoids unnecesary updating the layout

  ;Outcome variablen
  runnr
  output-file-name

  ;FIBE 1.0 response variables
  numFishers numFishing
  stock stockA stockB stockC stockD                                                                   ; Ecological response variables: all and regional
  accumCatchYearly accumCatchA accumCatchB accumCatchC accumCatchD catchBtickly
  accumProfitYearly
  fisherSatisfactionMean fisherSatisfactionSD
  giniCatch giniProfit

  ;; variables indicating the underlying reasons for not fishing
  notFishing
  numLayingLow numThinkFishIsScarce numSatisfied numLowCapital
  numFishersWgoodSpot percFishersWgoodSpot numExpectNoProfit numWantToBeHome

  meanTimesFishing
  sdTimesFishing sumTimesFishing maxTimesFishing minTimesFishing medianTimesFishing       ; Social response variables: all

  numFishingTrawls meanCatchTrawls sdCatchTrawls meanCapitalTrawls sumCapitalTrawls giniTrawls        ; Social (incl economical) response variables: Offshore trawler fisher
  numFishingCoastls meanCatchCoastls sdCatchCoastls meanCapitalCoastls sumCapitalCoastls giniCoastls  ; Social (incl economical) response variables: Coastal fisher
  ]

patches-own [
  region                ; indicates which of the 4 region this patch belongs to. Sea 1: A = close, B = medium far, C= far away; Sea 2: D = far away but other sea/fish stock/rules or NULL
  density               ; indicates how much fish (relative to the fish stock in this region) populates this patch
  fish-stock            ; indicates the number of fish on this patch
  growth-rate           ; the rate of growth on this patch
  regenAmount           ; amount the stock has grown this tick
  patch-stock-after-regrowth  ; presents the stocksize before fishing directly after regrowth
  patch-carrying-capacity     ; the amount of fish that can live/sustain here
]

fishers-own [
 myStyle              ; represents the style the fisher is displaying (depending on the simulation this remains constant or is changeable over time), in the initialisation it supports setup, during the simulation it characterised the settings (label not driver)
 satisfaction         ; represents how satisfied a fisher is at a current time
 goodSpot-threshold   ; threshold for the agents with a satisficing seleciton procedure to assess whehte a fishing spot is satisfactory based on the stock there
 f_capital            ; amount of money the fisher (household/company)? holds
 prev-capital         ; capital of last time step
 profit memory_profit accumulatedProfit accumProfitThisYear ; amount of profit - this tick, memory of...
 lowCatchCnt          ; amount of ticks in the year with a low catch, used to assess whether the fisher thinks there is not enough fish, it is getting scarce
 catch accumulatedCatch accumCatchThisYear memory-catch memoryCatchTick;amount of fish caught - this tick, over all ticks, memory of...
 memory-catchA memory-catchB memory-catchC memory-catchD ; region dependend memory of catches
 growth-perception    ; list used to asses the perception of growth based on the the memory of catches
 expected-catchA expected-catchB expected-catchC expected-catchD ; expected catches
 thinkFishIsScarce    ; bool to indicate whether the fisher thinks the fish is scarce

 regionPref           ; expectation based region preference of the agents
 memory-goodSpotsA memory-goodSpotsB memory-goodSpotsC memory-goodSpotsD ; knowledge of good spots to fish in region A,B,C,D
 memory-fishAtSpot    ; memory of the amount of fish on locations
 memory-visitedSpots  ; memory of the actual location of fishing corresponding with memory-fishAtSpot
 ffinding-knowledge   ; skill level in ability to find fish [0,1]
 catch-ability        ; number of fish that one can maximally fish based on gear the efficiency of actually catching fish [0,5000]?? to calibrate
 cost-equipment       ; cost of gear {low,medium,high} is directly connected to catchability
 cost-travel          ; fishing in different sea regions {a,b,c,d} cost (includes the vessel, fuel, fishing on the spot)
 cost-existance       ; {l,m,h} cost for the fisher to maintain its existance as fisher (company cost rent, interest, etc) and as a person (household/subsistence cost)
 cost                 ; total costs of the agents
 technology           ; boolean indicating the fisher has technology (e.g. radar) to scan for fish in its vinicity , i.e. enables to find fish
 collegues            ; boolean indicating the fisher has collegues with whom it exchanges information, e.g. where to find fish
 partner              ; boolean indicating the fisher has a partner it can rely on for income

 willFish             ; boolean indicating the decision of a fisher to go fishing or not
 atHome               ; boolean indicating a fihsing is at home
 layLow               ; boolean indicating the way a fisher does not fish (layLow = reducing cost, otherwise just a break)
 cntWentFishing       ; counter for the amount of ticks during a run in which the agent went out to fish, i.e. willFish is true
 cntWentFishingPeriod ;  counter for the amount of ticks during last period in which the agent went out to fish, i.e. willFish is true
 notAtSeaThreshold    ; number of ticks the agent can be abstain from being at sea - only for the agents that value being a fisher {week, month, season}
 notAtSeaCnt          ; number of ticks the agent was not at sea in a row
 movedToday           ; boolean indicating that the fisher already decided where to go today

 profit-thresh        ; threshold of profit a fishing trip should be before an trawler even decides to go out (higher than the costs of going out)
 gonefishing          ; I am still at sea and consider to stay another day
 myLastFishSpot       ; indicates the spot where fisher fished last time
 atSea                ; boolean indicating that the fisher is at sea   (use to indicate time effects, fishers do not move literally back and forth to land)
 atSeaCnt             ; counter to check that fishers are not at sea longer that 2 days - based on emprical knowledge that vessels do not allow to cool/store fish for longer
 hitGoodSpotCnt       ; counter when the fisher hits one of the hotspots (medium & high dense fish areas)
 goodSpotToday        ; boolean whether one found a good spot today

 storingcapacity      ; amount of fish an agent can store onboard before returning to port
 fish-onboard         ; amount of fish currently stored on the vessel
 jumped               ; indicates that a fisher on a multi-day trip moved from the spot he was

 homeTime-satisfaction growth-satisfaction ; satisfaction levels of the agent based on being home vs having an income
 expectNoProfit wannaBeHome ; indicators reason for not fishing

 ]

;;;;;;;;;;;;;; GO PROCEDURES - RUNNING THE SIMULATION ;;;;;;;;;;;;;;

;; The main process of the simulation that triggers
;; the fishers to decide and may fish every tick, the fish reproduces on a yearly base
to go

  set badWeather getWeather
  let yearTick ((ticks mod YEAR) < 1)
  set catchBtickly 0

  ifelse (yearTick)
    [ ask patches with [region != NULL] [ update-stock ]
      if any? fishers [
        ask fishers [ set lowCatchCnt 0 ]
        go-tickly
      ]
      update-response-vars-periodicly
  ]

  [ set yearTick false
    if ((ticks mod YEAR) = 1) [ reset-counters ] ;first day of the year
    go-tickly ]

  update-layout
  if ticks >= end-of-sim [ stop ]
  tick
end

;; Triggers all the functions and actions that should be executed every simulation day/tick
to go-tickly
  if not(ecologyOnly) [
    ask fishers [
      set movedToday false
      decide-fishOrNot ]
    ask fishers with [ willfish = true and gonefishing = true ] [ decide-fishSpot ] ;first those that are already at sea decide where to go (multi-day - trawlers)
    ask fishers with [ willfish = true and not atSea ] [ decide-fishSpot ] ;then the others

    ask fishers [
      execute-decision
      ;show (sentence "accumulated cata (B C D): "accumCatchB " " accumCatchC " " accumCatchD)
      update-memory
      update-satisfaction ]
  ]
  update-response-vars-tickly
end

;;;;;; Resource functions


;; Updates the fish-stock at a patch by mimicking the regrowth/reproduction of fish given the particular characteristics of that site and species
to update-stock
  set regenAmount round(fish-stock * growth-rate * (1 - (fish-stock / PATCH-CARRYING-CAPACITY)))
  set fish-stock fish-stock + regenAmount
  set patch-stock-after-regrowth fish-stock
end

;;;;;; Agent functions

;; The agents decision model is based interface selected decision models
to decide-fishOrNot
  if myStyle = "archipelago" [ satisfice-lifestyle ]          ;bounded rational with satisfising as selection process - values maintaining being at sea, being selfreliant, close to home
  if myStyle = "coastal" [ optimise-lifestyle-and-growth ]    ;bounded rational with optimising as selection process - values monetary growth, being at sea, being selfreliant, close to home
  if myStyle = "trawler" [ optimise-growth ]                  ;bounded rational with optimising as selection process- values monetary growth
end

; Makes the agents execute the decision made
; Fishers that go fishing fish
; they all affect/set their cost and income
to execute-decision
  ifelse (willFish = true) [
    set atHome false
    display
    ;show (word "I AM fishing!")
    go-fish
    set myLastFishSpot patch-here
  ]
  [ ; Not fishing!
    set atHome true
    if ([ region ] of patch-here !=  NULL) [ move-to one-of land ]
    set cost-existance getMyExistCost myStyle
    ifelse (laylow) [ ; reduce cost or alternative income
      ifelse partner
      [ set cost-existance 0.5 * cost-existance ]  ;If one has a partner one can reduce cost by depending on the other and spending less
      [ set cost-existance 0.25 * cost-existance ]] ;Without a partner one can reduce cost by spending less
    [ ; do-nothing  - mainly for the trawler and coastal
      set gonefishing false
      set jumped false ]

    set cost cost-existance
    set catch 0
    set fish-onboard 0
  ]

  ifelse (gonefishing = true) ;will not return to land
    [ set profit 0 - cost
      set atSeaCnt atSeaCnt + 1 ]
    [ set profit fish-onboard * fish-price - cost       ; TODO replace cost, also separate getting profit when landing - differentatie between fisher that go back to the harbour and those doing a multitr
      set fish-onboard 0
      set atSea false
      set atSeaCnt atSeaCnt + 1
    ]

  ;show (word "today I caught: " catch " and I earned: " profit)
  set accumulatedProfit accumulatedProfit + profit
  set accumProfitThisYear accumProfitThisYear + profit
  set prev-capital f_capital
  set f_capital f_capital + profit
  ;show (sentence "capital: " f_capital)
end

;########## DECIDE WHETHER TO GO FISH ###########

;; The choice to fish or not is driven by the need to fish (i.e. subsistence - breaking even in cost)
to satisfice-lifestyle
  let lastcatchIndex min (list (length memoryCatchTick) 5); length of the memory of catches or a week
  let catch-last-week sum (sublist memoryCatchTick 0 lastcatchIndex)
  ;show (sentence "satisfice-lifestyle: last 5 catches " (sublist memoryCatchTick 0 lastcatchIndex) " = last weeks catch = " catch-last-week)
  let cost-ideal-week (7 * cost-existance + 5 * cost-travel + 5 * cost-equipment)

  let doneEnough (catch-last-week * fish-price) >= cost-ideal-week ; fisher has done enough this week
  ifelse (doneEnough = true)
  [ set satisfaction 1
    ;show (sentence "Satisfice-lifestyle: doneEnough= " doneEnough)
  ]
  [ set satisfaction (catch-last-week * fish-price) / cost-ideal-week ]
  set thinkFishIsScarce lowCatchCnt > 0.75 * memory-spatial-length  ; when the amount of catches resemble the amount of good places in mind, the agent tried all spots and will decide that there is not enough fish anymore
  ;if thinkFishIsScarce [ show (sentence "Satisice-lifestyle - I think fish is scarce :" thinkFishIsScarce " - low catch count: " lowCatchCnt) ]
  ;show (sentence "profit-last-week: " (catch-last-week * fish-price))
  ifelse (badWeather) [
    set willFish false
    ;show ("Satisfice-lifestyle: Will not fish, bad weather")
    ;laylow will stay what it was last time
    set notAtSeaCnt notAtSeaCnt + 1
  ]
  [ ifelse (thinkFishIsScarce)
    [ set willFish false ; layLow - reduce costs!
      set layLow true;
      set notAtSeaCnt notAtSeaCnt + 1
      ;show (sentence "Satisfice-lifestyle: Will not fish but am not satisfied but fish is scarce")
    ]
    [ ifelse (not (doneEnough) or f_capital < 0)
      [ set willFish true
        set layLow false
        set notAtSeaCnt 0 ]
      [ set willFish false
        set layLow false;
        set notAtSeaCnt notAtSeaCnt + 1 ]]
  ]
end

;; Deciding to fish or not is a tradeoff between spending time at home and being a fisher with a growing capital/fishing enterprise
to optimise-lifestyle-and-growth

  ifelse (badWeather) [ set willFish false ]
  [
    let expected-cost NULL
    let expected-income NULL
    let expected-catch catch-ability

    ifelse (not beginning-season and ticks > WEEK) [
      set-catch-expectation-and-regionPref
      set expected-catch max (list expected-catchA expected-catchB)
      ;show (sentence "region-pref=" regionPref " after just calculating my catch expectations A("round(expected-catchA)") B("round(expected-catchB)")")
    ][ ifelse (random 2 > 0)
      [ set regionPref A ]
      [ set regionPref B ]
    ]
    set expected-income (expected-catch * fish-price)
    set expected-cost (cost-equipment + cost-existance + (getTravelCost regionPref myStyle))
    let expected-profit-stay 0 - cost-existance
    let expected-profit-go expected-income - expected-cost
    ;Up to this point behaviour is the same as the trawler - optimise growth

    set wannaBeHome false
    set expectNoProfit false
    ifelse (expected-profit-go > expected-profit-stay) [
      ifelse (homeTime-satisfaction < home-satisf-threshold and homeTime-satisfaction < growth-satisfaction) [
        ;show (sentence "not fishing because I want to spend time at home. " precision homeTime-satisfaction 2 " > sat-growth" precision growth-satisfaction 2 ) ; growth-satis >= homeTime-satis
        set wannaBeHome true
        set willFish false]
      [ set willFish true
        ;show (sentence "go fishing, not satisfied on my growth - satHome = " precision homeTime-satisfaction 2 " <= sat-growth" precision growth-satisfaction 2)
      ]
    ]
      [ ;show "not fishing because is is not profitable"
        set expectNoProfit true
        set willFish false ]
  ]

  ifelse (willFish = false) [
    set notAtSeaCnt notAtSeaCnt + 1]
  [ set notAtSeaCnt 0 ]
end

;; Fisher decides to go fishing or not, or whether it will continue to fish (multiday trip, stay longer at sea)
;; A fisher goes fishing when it expects to have most monetary benefit from going (profit fishing > profit not-fishing, implying that it expects to be able to catch fish in right amount, if the fish population is considered too low the fisher doesnot go out
;; Continuing to fish follows the same reasoning, but the decision is about staying longer at sea (less travel cost) and
;; the consequence of not filling its vessel last tick. We thus 'artifically' move this choice to this tick but correct for the profit in retrospect.
to optimise-growth
  let expected-cost NULL
  let expected-income NULL
  let expected-catch catch-ability

  ifelse not(goneFishing) [   ;not at sea
    ifelse (not beginning-season and ticks > WEEK) [
      set-catch-expectation-and-regionPref  ; TODO add some influence of the last years (e.g. bad year/trend in a particular region, don't go their)
      set expected-catch max (list expected-catchB expected-catchC expected-catchD)
      ;show (sentence "not at sea: region-pref=" regionPref " after just calculating my catch expectations B("expected-catchB") C("expected-catchC") D("expected-catchD")")
    ][
      let rnd random 3
      if rnd = 0 [ set regionPref B ]
      if rnd = 1 [ set regionPref C ]
      if rnd = 2 [ set regionPref D ]
    ]
    set expected-income (expected-catch * fish-price)
    set expected-cost (cost-equipment + cost-existance + (getTravelCost regionPref myStyle))
  ]

  [ ; gonefishing = TRUE, i.e. consideration multi-day trip
    let fishWish storingcapacity - fish-onboard
    let fishVicinity [ fish-stock ] of patch-here
    ask patches in-radius 1 [ set fishVicinity fish-stock + fishVicinity ]
    let expected-travel-cost 0
    let currentRegion [region] of patch-here
    set-catch-expectation-and-regionPref  ; TODO add some influence of the last years
    ;show (sentence "at sea: region-pref=" region-pref " after just calculating my catch expectations B("expected-catchB") C("expected-catchC") D("expected-catchD")")

    ifelse (fishVicinity >= fishWish)
    [ set expected-catch fishWish
      set regionPref currentRegion ]
    [ ; not enough fish nearby, experience based expectations
      ifelse max(list expected-catchB expected-catchB expected-catchD) < fishWish  ; catch-expectation is lower that the fishWish - catch what you can with minimal travelling - stayin your region
      [ set expected-catch fishVicinity
        set expected-travel-cost (getTravelCost currentRegion mystyle) / 8
        set regionPref currentRegion
        ]
      [ ;expected catch > fishWish
        set expected-catch fishWish
        if (currentRegion = B) [ set expected-travel-cost get-exp-travelcost B C D expected-catchB expected-catchC expected-catchD fishWish ]
        if (currentRegion = C) [ set expected-travel-cost get-exp-travelcost C B D expected-catchC expected-catchB expected-catchD fishWish ]
        if (currentRegion = D) [ set expected-travel-cost get-exp-travelcost D B C expected-catchD expected-catchB expected-catchC fishWish ]
      ]]
    set expected-cost (cost-equipment + cost-existance + expected-travel-cost)                      ; cost to stay at sea and fish at or close to current position)
    set expected-income (expected-catch * fish-price)
  ]

  let expected-profit-stay 0 - cost-existance
  let expected-profit-go expected-income - expected-cost

  ;show (sentence "expected profit-stay"  expected-profit-stay " expected profit go: " expected-profit-go)
  ifelse (expected-profit-go > expected-profit-stay)  ; could results in continuing to fish without having a profit but having less debts
  [ set willFish true
    set expectNoProfit false ]
  [ set willFish false
    set expectNoProfit true
    set movedToday false
    if gonefishing [ land-fish ]]
end


;########## DECIDE WHERE TO GO FISH ###########

;; The fisher decides where to go fishing
;; If still at sea (goneFishing) it checks whether the current spot is allows for filling the vessel
;; If not at sea OR in need for a good fishing spot a fisher may decide for a spot based on its knowledge (goodSpots memory) or what other fishers do
;; depending on the attributes of a fisher (colleagues y/n and # fishers at a certain spot)
to decide-fishSpot
  ;when having/sensitive to collegues AND probability towards following others (sensitive to amount of fishers at one spot)
  let fishingSpot patch MAXXD MINYA
  let stayPut false

  ; Decide where to fish (multi-day trippers, fisher is already at sea)
  if (gonefishing) [
    if technology [
      let currentspot patch-here
      uphill fish-stock
      if [ region ] of patch-here != [ region ] of currentspot [
        move-to currentspot ]]
    if ([ fish-stock ] of patch-here < (storingcapacity - fish-onboard)) [
      set stayPut true
  ]]

  ; Decide where to fish (all)
  if (not stayPut) [
    set jumped true

    ifelse (not(socialInfluence = "none") and collegues and random 11 < 8) ; most of the time follow social norm
      [ ifelse socialInfluence = "descriptiveNorm"
        [ set fishingSpot get-fishSpot-descriptive-norm ]
        [ set fishingSpot get-fishSpot-expertise ]
        if fishingSpot = patch MAXXD MINYA [
          set fishingSpot get-fishSpot-knowledge regionPref
    ]]
    [ ;show "in fishing spot now"
      set fishingSpot get-fishSpot-knowledge regionPref
      if (fishingSpot = nobody) [ print "a. fishingspot is a nobody" ]
    ]

    ifelse (fishingSpot = nobody) [
      print "b. fishingspot is a nobody"
      move-to one-of regionA ]
    [ move-to fishingSpot ]

    if technology [
      let currentspot patch-here
      uphill fish-stock        ; fisher moves to the patch with the heighest fish stock
      if ([ region ] of patch-here != [ region ] of currentspot) ; unless this is a patch from a different region then it remains where it was
        [ move-to currentspot ]
    ]
  ]
  set atSea true
  set movedToday true
end


;; decide on fishspot (gridcell) based purely on memory of good spots
;; if no idea a random spot is chosen in the region the fisher fished last
;; @param prefReg Preferred region
;; @report A fish spot
to-report get-fishSpot-knowledge [ prefReg ]
  ;show (sentence "in get-fishSpot-knowledge now! prefReg = " prefReg)
  let fishSpot patch 0 0
  let mem-goodSpots memory-goodSpotsA
  ;if (prefReg = A) [ set mem-goodSpots memory-goodSpotsA ]
  if (prefReg = B) [ set mem-goodSpots memory-goodSpotsB ]
  if (prefReg = C) [ set mem-goodSpots memory-goodSpotsC ]
  if (prefReg = D) [ set mem-goodSpots memory-goodSpotsD ]

  ifelse (any? mem-goodSpots)
  [ set fishSpot one-of mem-goodSpots
    let rgn [ region ] of fishSpot
    if (rgn != prefReg ) [ show "Syst.err - get-fishpot-knowledge-from my memory: returning a fishspot that is not of my preference" ]
    if (rgn = NULL ) [ show "Syst.err returning land as fishSpot, which is part of my memory! really bad" ]]
  [ set fishSpot one-of patches with [ region = prefReg ]
    ifelse (fishSpot = nobody)
    [ show (sentence "Syst.err: 2 the patch is not a fishing patch " fishSpot " get-fishSpot-knowledge prefReg was" prefReg ) ]
    [ let rgn [ region ] of fishSpot
      if (rgn != prefReg ) [ show "Syst.err - get-fishpot-knowledge-random from my prefRegion: returning a fishspot that is not of my preference" ]
      if (rgn = NULL) [ show "returning land as fishSpot, have no memory of good spots" ]]]

  if (random 2 > 0) [
    ask fishSpot [
      let rgnFs [ region ] of fishSpot
      let tmp one-of neighbors with [ region = rgnFs ]
      ifelse (tmp = nobody)
      [ show (sentence "Syst.err: 3 no neighbor of within my region - this is incorrect there are always neighbors within my region - TO FIX: " tmp ) ]
      [ set fishSpot tmp ]
  ]]
  let rgn [ region ] of fishSpot
  if (rgn = NULL ) [ show "returning land as fishSpot" ]

  if (rgn != prefReg) [
    show ("returning a fishspot that is not in my preferred region")]
  report fishSpot
end

;; Reports a fish spot of one to the other fishers that is considered to have most knowledge
;; @report A fish spot
to-report get-fishSpot-expertise
  let fisherSet trawlers
  let myKnowledge ffinding-knowledge
  let myRegPref regionPref
  let othersPrefForRgn false
  if (mystyle = "coastals") [ set fisherSet coastals ]
  let expertsOut fisherSet with [ movedToday = true and ffinding-knowledge >= myKnowledge ] ; consider someone expert when having the same or better knowledge as oneself
  let expertsAtPrefRegion expertsOut with [ region = myRegPref ]
  let spot patch MAXXD MINYA
  ifelse (any? expertsAtPrefRegion)
    [ set spot [ patch-here ] of (one-of expertsAtPrefRegion)]
  [ set spot get-fishSpot-knowledge myRegPref ]

    let rgn [ region ] of spot
  report spot
end

;; Report whethr someone wants to be at a given spot
;; @param spot A given spot
;; @report Yes or No (Boolean)
to-report doesAnyoneWantToBeHere [ spot ]
  let rgn [ region ] of spot
  let prefs [regionPref] of turtles-on spot
  ifelse not (empty? prefs) [
    if (rgn = A) [ report member? A prefs ]
    if (rgn = B) [ report member? B prefs ]
    if (rgn = C) [ report member? C prefs ]
    if (rgn = D) [ report member? D prefs ]
  ] [ report true ]
end


;; reports a fish spot where most fishers are in the region of interest following norm of what everybody does (descriptive norm)
;; @report A fish spot
to-report get-fishSpot-descriptive-norm

  if ( myStyle = "trawler") [
    let numAtB count (turtles-on regionB) with [ myStyle = "trawler" ]
    let numAtC count turtles-on regionC
    let numAtD count turtles-on regionD

    if (numAtB > numAtC and numAtC > numAtD) [ report fishspot-with-most-fishers regionB ]
    if (numAtB > numAtC and numAtC < numAtD) [ report fishspot-with-most-fishers regionD ]
    if (numAtB < numAtC and numAtC > numAtD) [ report fishspot-with-most-fishers regionC ]
    if (numAtB < numAtC and numAtC < numAtD) [ report fishspot-with-most-fishers regionD ]

    if (numAtB = numAtC and numAtB = numAtD) [ report fishspot-with-most-fishers (patch-set regionB regionC regionD)]
    if (numAtB = numAtC) [ report fishspot-with-most-fishers (patch-set regionB regionC) ]
    if (numAtB = numAtD) [ report fishspot-with-most-fishers (patch-set regionB regionD) ]
    if (numAtC = numAtD) [ report fishspot-with-most-fishers(patch-set regionC regionD) ]
    show "Syst.err in get-fishSpot-descriptive-norm: comparing number of turtles on regions has a case that is not accounted for - FIX IT!"
  ]
  if (myStyle = "coastal") [
    let numAtA count (turtles-on regionA) with [ myStyle = "coastal" ]
    let numAtB count (turtles-on regionB) with [ myStyle = "coastal" ]
    if (numAtA > numAtB) [ report fishspot-with-most-fishers regionA ]
    ifelse (numAtA < numAtB)
    [ report fishspot-with-most-fishers regionB ]
    [ report fishspot-with-most-fishers (patch-set regionA regionB) ]
  ]
  show "Syst.err in get-fishSpot-descriptive-norm: called for an agent that isn't a trawler or coastal - FIX IT!"
  report patch MAXXD MINYA
end

;; returns a fishspot in a particular region with the most fishers
;; this spot must at least have IS-A-CROWD (2) fishers
;; @param region-patches Set of patches in a certain region
;; @report A fish spot
to-report fishspot-with-most-fishers [ region-patches ]
  let maxSpot patch MAXXD MINYA
  let maxClose 0
  ask turtles-on region-patches [
    let rgn [ region ] of patch-here
    let nrClose (count turtles-here with [ movedToday = true ] ) + (count (turtles-on neighbors with [ region = rgn ]) with [ movedToday = true ])     ; NOTE: this reach needs to be aligned with the reach of scanning due to technology - what scope a fisher can 'see' the fish density
    if (nrClose > maxClose) [
      set maxClose nrClose
      set maxSpot patch-here
    ]
  ]

  let fishSpot patch MAXXD MINYA
  if (maxClose >= IS-A-CROWD) [ set fishSpot maxSpot ]

  if (fishSpot = nobody) [
    ;print (sentence "Syst.err in fishspot-with-most-fisher results in a fish spot that is a nobody")
    set fishSpot patch MAXXD MINYA
  ]
  report fishSpot
end

;########## BEHAVE - ACTION EXECUTION ###########

;;The fisher executes its behavioural decision: goes fishing for as long as the effort indicates
;;as a consequence the fisher has some catch and related profit and the cod-stock is reduced.
;;Archelago and trawler catch fish on 1 patch, the coastal spreads over multiple patches
to go-fish
  let fstock [ fish-stock ] of patch-here
  ;show (sentence "go-fish: fishstock " fstock)
  let currentRegion [ region ] of patch-here

  ifelse (mystyle = "coastal") [  ;fishes with nets - bigger reach (catch over 2 patches)
    let otherPatch one-of neighbors with [ region = currentRegion ]
    let fstock2 [ fish-stock ] of otherPatch
    let ctch round(0.5 * catch-ability)
    let resCtch catch-ability - ctch
    ifelse ((fstock < ctch) xor (fstock2 < resCtch)) [  ;one of the two stocks is not sufficient to reach catchability
      if (fstock < ctch) [
        set ctch fstock
        set resCtch min(list (catch-ability - ctch) fstock2 ) ]
      if (fstock2 < resCtch) [
        set resCtch fstock2
        set ctch min (list (catch-ability - resCtch) fstock) ]
    ][ ;there is either plenty of fish OR not enough - the catch will be equally distributed over the two or just takes what is left
      if (fstock < ctch) [ set ctch fstock ]
      if (fstock2 < resCtch) [ set resCtch fstock2 ]
    ]
    ask patch-here [ set fish-stock fstock - ctch ]    ; catch half of catchability or what is left on this patch
    ask otherPatch [ set fish-stock fstock2 - resCtch ]; idem
    set catch ctch + resCtch
  ]
  [ ; not coastals
    set catch min list catch-ability fstock
    let newstock fstock - catch
    ask patch-here [ set fish-stock newstock ]
  ]

  ifelse (myStyle = "trawler")[
    let space-remaining storingcapacity - fish-onboard
    set catch min list catch space-remaining
    set fish-onboard fish-onboard + catch ]
  [ set fish-onboard catch ] ; myStyle = archipelago or coastal

  ;set the costs
  ifelse ( myStyle = "archipelago") [
    set cost-existance LOW-COST-EXISTANCE  ; TODO think of a way to not describe this 'label' dependent
    set cost-travel getTravelCost currentRegion myStyle ]
  [ ifelse ( myStyle = "coastal") [
    set cost-existance MEDIUM-COST-EXISTANCE  ; TODO think of a way to not describe this 'label' dependent
    set cost-travel getTravelCost currentRegion myStyle]
  [ if ( myStyle = "trawler") [
      ifelse (gonefishing = false)
      [ set cost-travel getTravelCost currentRegion myStyle ]
      [ if jumped = true
        [ set cost-travel (getTravelCost currentRegion myStyle) / 2
          set jumped false ]]
      ifelse ((storingcapacity = fish-onboard) or gonefishing = true) ; (atSeaCnt > 1)
      [ set gonefishing false ]  ;fished all I can carry OR already went on a multi-day trip
      [ set gonefishing true ]   ;didn't fish as much as I can carry
  ]]]

  reduce-stock currentRegion catch
  set cost cost-existance + cost-equipment + cost-travel
  set cntWentFishing cntWentFishing + 1
  set cntWentFishingPeriod cntWentFishingPeriod + 1

  ;response variables
  ;show (word "catch: " catch "; catch-ability: " catch-ability "; fstock: " fstock "; fish-onboard" fish-onboard)
  set accumulatedCatch accumulatedCatch + catch
  set accumCatchThisYear accumCatchThisYear + catch

  let dens [ density ] of patch-here
  ifelse (dens = MEDIUM or dens = HIGH) [
    set goodSpotToday 1
    set hitGoodSpotCnt hitGoodSpotCnt + 1 ]
  [ set goodSpotToday 0 ]

end

;function that 'corrects' for the fishers that considered to do a multi-day trip
; but didn't go for it afterall, making that the catch hasn't been landed last tick and will be immediately
; be processes - sold (profit calculation and memory of profit updated).
to land-fish
  set profit fish-onboard * fish-price - cost
  set fish-onboard 0
  set f_capital f_capital + fish-onboard * fish-price ;the cost have already been added to the f_capital
  set memory_profit fput profit memory_profit
  if (length memory_profit > memory-time-length)
    [ set memory_profit but-last memory_profit ]
  set gonefishing false
  set atSea false
end


;########## UPDATE ###########

to reduce-stock [ regionx catchx ]
  if (regionx = A)[
    ;show (sentence "new codStock ="  stockA "(stockA) -"  catch "(catch)")
    set stockA max (list 0 (stockA - catchx))
    set accumCatchA accumCatchA + catchx
    set accumCatchA accumCatchA + catchx ]
  if (regionx = B)[
    set stockB max (list 0 (stockB - catchx))
    set accumCatchB accumCatchB + catchx
    set catchBtickly catchBtickly + catchx
    set accumCatchB accumCatchB + catchx ]
  if (regionx = C)[
    set stockC  max (list 0 (stockC - catchx))
    set accumCatchC accumCatchC + catchx
    set accumCatchC accumCatchC + catchx ]
  if (regionx = D)[
    set stockD  max (list 0 (stockD - catchx))
    set accumCatchD accumCatchD + catchx
    set accumCatchD accumCatchD + catchx ]
end

;; Returns the region based travel cost
;; In case the fuel-subsidy scenario is active (>0) the travel costs are reduced by that percentage in ALL regions.
;; @param regionX Region
;; @param style Fishing style of the agent
;; @report Costs for travelling
to-report getTravelCost [ regionx style ]
  ifelse (fuel-subsidy > 0)
  [ ifelse (regionx = A)
    [ report LOW-COST-TRAVEL - (fuel-subsidy * LOW-COST-TRAVEL) ]
    [ ifelse (regionx = B)
      [ ifelse (style = "coastal")
        [ report MEDIUM-COST-TRAVEL - (fuel-subsidy * MEDIUM-COST-TRAVEL) ]
        [ report MEDIUM-COST-TRAVEL-BIGVESSEL - (fuel-subsidy * MEDIUM-COST-TRAVEL-BIGVESSEL) ]]   ;trawler
      [ ifelse (regionx = C)
        [ report HIGH-COST-TRAVEL - (fuel-subsidy * HIGH-COST-TRAVEL) ]
        [ ifelse (regionx = D)
          [ report HIGH-COST-TRAVEL - (fuel-subsidy * HIGH-COST-TRAVEL) ]
          [ show (sentence "Syst.err: in getTravelCost, the travel cost are called for a non sea patch in region: " regionX " SOLVE IT!" )
            report 0 ]
    ]]]]

  [ ;show "fuel subsidy = 0 "
    ifelse (regionx = A)
      [ report LOW-COST-TRAVEL ]
      [ ifelse (regionx = B)
        [ ifelse (style = "coastal")
          [ report MEDIUM-COST-TRAVEL ]
          [ report MEDIUM-COST-TRAVEL-BIGVESSEL ]]
        [ ifelse (regionx = C)
          [ report HIGH-COST-TRAVEL ]
          [ ifelse (regionx = D)
            [ report HIGH-COST-TRAVEL ]
            [ show (sentence "Syst.err: in getTravelCost, the travel cost are called for a non sea patch in region: " regionX " SOLVE IT!" )
              report 0 ]
          ]]]]
end

;; Updates the satisfaction levels for coastal and trawler
;; Trawler satisfaction is based on the need to grow (profit)
;; Coastal based on the need to grow (profit) and to be home
;; Archipelago is updated in (satisfice-lifestyle), as this is satisfaction based
to update-satisfaction

if (myStyle = "coastal" OR myStyle = "trawler") [
  if ( f_capital < 0 ) [ set growth-satisfaction 0 ]
  let growth-indicator mean(modes growth-perception)   ; 0 contant profit, -1 negative profit, 1 growth
  ;show (sentence"update-satisfaction: growth-perception:" growth-indicator)
  ifelse (growth-indicator > 0 ) [   ; growth = max catch here, growth in that sense is not possible
    set growth-satisfaction growth-satisfaction + 0.1
    if (growth-satisfaction > 1) [ set growth-satisfaction 1 ]]
  [ ifelse (growth-indicator = 0) [
      set growth-satisfaction growth-satisfaction - 0.1 ]  ; constant profit
    [ set growth-satisfaction growth-satisfaction - 0.2 ]  ; opposite of growth
    if (growth-satisfaction < 0) [ set growth-satisfaction 0 ]]

  set satisfaction growth-satisfaction

  if (myStyle = "coastal") [
    ifelse (atHome = true) [
      set homeTime-satisfaction homeTime-satisfaction + 0.5
      if (homeTime-satisfaction > 1) [ set homeTime-satisfaction 1 ]]
    [ set homeTime-satisfaction homeTime-satisfaction - 0.1  ;in 10 days completely dissatisfied
      if (homeTime-satisfaction < 0) [ set homeTime-satisfaction 0 ]]
  set satisfaction (growth-satisfaction + homeTime-satisfaction) / 2
  ]
]
end

;; Update the memory using the FIFO principle (first in, first out)
;; Keeps track of the profits of the last 'memory-of-profits' time steps
to update-memory
  let indicator 0
  if (prev-capital > f_capital)[ set indicator -1 ]
  if (prev-capital < f_capital)[ set indicator 1 ]

  set growth-perception fput indicator growth-perception

  set memory_profit fput profit memory_profit
  if length memory_profit > memory-time-length
    [ set memory_profit but-last memory_profit
      set growth-perception but-last growth-perception]

  set memoryCatchTick fput catch memoryCatchTick

  if (willfish) [   ; only update the memory of catches and goodSpots if you went fishing
    let rgn [ region ] of patch-here
    set memory-catch fput catch memory-catch
    ifelse (catch < catch-ability)
    [ set lowCatchCnt lowCatchCnt + 1 ]
    [ set lowCatchCnt max(list (lowCatchCnt - 1) 0) ]

    if (rgn = A) [ set memory-catchA fput catch memory-catchA ]
    if (rgn = B) [ set memory-catchB fput catch memory-catchB ]
    if (rgn = C) [ set memory-catchC fput catch memory-catchC ]
    if (rgn = D) [ set memory-catchD fput catch memory-catchD ]

    if length memoryCatchTick >= memory-time-length [ set memoryCatchTick but-last memoryCatchTick ]
    if length memory-catch >= memory-time-length [ set memory-catch but-last memory-catch ]
    if length memory-catchA >= memory-time-length [ set memory-catchA but-last memory-catchA ]
    if length memory-catchB >= memory-time-length [ set memory-catchB but-last memory-catchB ]
    if length memory-catchC >= memory-time-length [ set memory-catchC but-last memory-catchC ]
    if length memory-catchD >= memory-time-length [ set memory-catchD but-last memory-catchD ]
    ;show (word "memory_catch" memory_catch)

    update-memory-goodSpots
  ]
end

;; updates the memory of goodSpots based on the catch
;; bad catch at spotX -> remove from memory
;; good catch at spotX -> if not in memory - add it and shuffle it
to update-memory-goodSpots
  let fishSpot patch-here
  let rgn [ region ] of fishSpot
  let fsX [ pxcor ] of fishSpot
  let fsY [ pycor ] of fishSpot
  let memory-goodSpots memory-goodSpotsA
  if (region = B) [ set memory-goodSpots memory-goodSpotsB ]
  if (region = C) [ set memory-goodSpots memory-goodSpotsC ]
  if (region = D) [ set memory-goodSpots memory-goodSpotsD ]

  ifelse (member? fishSpot memory-goodSpots) [
    if (catch < catch-ability) [   ;bad catch
      set memory-goodSpots memory-goodSpots with [ pxcor != fsX and pycor != fsY ]  ; remove the fishspot
        ;show (sentence "removing patch " fishSpot " from memory")
      ]];]

  [ if (catch > (catch-ability - 1)) [
    set memory-goodSpots (patch-set fishSpot memory-goodSpots)
    if (rgn = nobody) [
     show (sentence "adding a nobody " fishSpot " from region " rgn " to memory") ]]
   ]

  if (region = A) [ set memory-goodSpotsA memory-goodSpots ]
  if (region = B) [ set memory-goodSpotsB memory-goodSpots ]
  if (region = C) [ set memory-goodSpotsC memory-goodSpots ]
  if (region = D) [ set memory-goodSpotsD memory-goodSpots ]
end

;; Function calculates GINI of the catch or profit of the fishers, a measure of inequality of a distribution (Gini,1912),
;; 0 = equality; 1 + maximal inequality
;; Ratio of the areas on the Lorenz curve diagram (proportion of total S (e.g. income) corresponding the cumulative S of the x% of the population.
;; adapted the implementation at https://subversion.american.edu/aisaac/notes/netlogo-intro.xhtml#plotting-gini-coefficient-and-lorenz-curve
to-report calc-GINI [ accumVal agentSet ]
  if (not any? agentSet) [ report 0 ]
  let numAgents count agentSet
  let cumsum-sorted-catch 0
  ifelse (accumVal = "profit") [
    set cumsum-sorted-catch partial-sums sort [ accumulatedProfit ] of agentSet ]
   [ ;(accumVal = "catch")
     set cumsum-sorted-catch partial-sums sort [ accumulatedCatch ] of agentSet ]

  ;print (word "cumsum-sorted-catch: " cumsum-sorted-catch)
  let total-catch last cumsum-sorted-catch
  let normalized-catch n-values numAgents [ 0 ]
  ifelse (total-catch > 0 ) [
    set normalized-catch map [ [x] -> x / total-catch] cumsum-sorted-catch
    ;print (word "normalized-catch: " normalized-catch)
    let gaps n-values numAgents [ [x] -> (((x + 1) / numAgents) - item x normalized-catch)]
    report (2 * sum gaps / numAgents)                                  ;Gini = A/(A+B) = 2*A
    ;print (word "gaps: " gaps " gini: " precision gini 2)
  ][ report 0 ]   ;the rare case that there was no extraction before and in the following round there will also be no extraction
  ;print gini
end

;; Updates the output variables every tick
to update-response-vars-tickly

  set runnr behaviorspace-run-number
  set stockA sum [ fish-stock ] of regionA
  set stockB sum [ fish-stock ] of regionB
  set stockC sum [ fish-stock ] of regionC
  set stockD sum [ fish-stock ] of regionD
  set stock stockA + stockB + stockC + stockD

  if (not(ecologyOnly) and any? turtles) [
    let fishingFishers fishers with [ willFish = true ]
    set numFishing count fishingFishers
    set notFishing count fishers - numFishing

    ; underlying reasons for not fishing archipelago
    if (archipelago-fisher > 0 ) [
      set numLayingLow count fishers with [ layLow = true]
      set numThinkFishIsScarce count fishers with [ thinkFishIsScarce = TRUE and willFish = false ]
      set numSatisfied count fishers with [ willFish = false and satisfaction = 1 ]
      set numLowCapital count fishers with [ willFish = false and f_capital <= 0 ] ;this is not a real reason, it is more eventhough they have no/negative capital they do not go out.
    ]
    ; underlying reasons for not fishing coastals - bad weather, expects no profit, want to spend time at home
    if (coastal-fisher > 0 ) [
     set numExpectNoProfit count fishers with [ willFish = false and expectNoProfit = true ]
     set numWantToBeHome count fishers with [ willFish = false and wannaBeHome = true ]
    ]
    ; underlying reasons for not fishing coastals - bad weather, expects no profit, want to spend time at home
    if (offshore-trawler-fisher > 0 ) [
      set numExpectNoProfit count fishers with [ willFish = false and expectNoProfit = true ]
    ]

    set accumProfitYearly sum [ accumProfitThisYear ] of fishers
    set accumCatchYearly sum [ accumCatchThisYear ] of fishers

    set fishingAtA 0
    set fishingAtB 0
    set fishingAtC 0
    set fishingAtD 0
    ask fishers with [ willfish = true ] [
    let rgn [ region ] of patch-here
    if (rgn = A) [ set fishingAtA fishingAtA + 1 ]
    if (rgn = B) [ set fishingAtB fishingAtB + 1 ]
    if (rgn = C) [ set fishingAtC fishingAtC + 1 ]
    if (rgn = D) [ set fishingAtD fishingAtD + 1 ]
  ]
    set numFishersWgoodSpot sum [ goodSpotToday ] of fishers with [ willFish = true ]
    ifelse (numFishing = 0) [
      set percFishersWgoodSpot 0
    ]
    [ set percFishersWgoodSpot numFishersWgoodSpot / numFishing ]
  ]
  ifelse any? fishers
  [ set fisherSatisfactionMean mean [ satisfaction] of fishers
    if (count fishers > 1) [
      set fisherSatisfactionSD standard-deviation [ satisfaction] of fishers]]
  [ set fisherSatisfactionMean 0 ]
end

;; Updates the output variables every year
to update-response-vars-periodicly
  ;agent variables
  if not(ecologyOnly) and (any? fishers) [
    if ticks > 0 [
    set meanTimesFishing mean [ cntWentFishingPeriod ] of fishers
    set numFishers count fishers

    ask fishers [
      ;show (sentence "cntWentFishingPeriod: " cntWentFishingPeriod)
      set cntWentFishingPeriod 0
    ]
      set giniCatch calc-GINI "catch" fishers
      set giniProfit calc-GINI "profit" fishers

   ;print (sentence "responsevar (halfyear:" (ticks / HALFYEAR) "): stock-C " stockC " catch-indiv " meanMeanCatch " totalCatch " accumCatch " timesFishing " meanTimesFishing)
  ]]

end
@#$#@#$#@
GRAPHICS-WINDOW
195
45
503
390
-1
-1
6.0
1
10
1
1
1
0
0
0
1
0
49
0
55
1
1
1
ticks
10.0

BUTTON
10
10
65
43
NIL
setup
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
68
10
123
43
NIL
go
T
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
125
10
180
43
go once
go
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

SLIDER
10
165
185
198
offshore-trawler-fisher
offshore-trawler-fisher
0
100
0.0
1
1
NIL
HORIZONTAL

PLOT
530
45
775
190
Stock in region C & D
NIL
NIL
0.0
10.0
0.0
1130000.0
true
true
"" ""
PENS
"stockC" 1.0 0 -13345367 true "" "if (ticks > 0) [ plot stockC ]"
"stockD" 1.0 0 -14835848 true "" "if (ticks > 0) [ plot stockD ]"
"MSY" 1.0 0 -2674135 true "" "if (ticks > 0) [ plot MSY-STOCK-C ]"

TEXTBOX
15
410
165
428
Environment
16
0.0
1

TEXTBOX
210
690
319
709
Monetary
11
0.0
1

TEXTBOX
205
365
220
383
A
14
9.9
1

TEXTBOX
25
610
52
628
B
13
9.9
1

TEXTBOX
205
225
220
243
C
14
9.9
1

TEXTBOX
355
225
370
243
D
14
9.9
1

TEXTBOX
14
485
151
503
Initial stocksize
11
0.0
1

TEXTBOX
15
555
133
574
Reproduction-rate
11
0.0
1

SWITCH
290
10
420
43
showHotSpots
showHotSpots
0
1
-1000

TEXTBOX
205
320
220
338
B
14
9.9
1

TEXTBOX
15
285
120
303
Scenarios
15
0.0
1

SLIDER
200
440
365
473
memory-spatial-length
memory-spatial-length
0
200
20.0
1
1
NIL
HORIZONTAL

PLOT
780
340
1040
480
decision to go fish
NIL
NIL
0.0
0.0
0.0
0.0
true
true
"" ""
PENS
"# out to fish" 1.0 0 -9276814 true "" "plot count turtles with [ willFish = true ]"
"# archips fishing" 1.0 0 -13840069 true "" "plot count archipelagos with [ willFish = true ]"
"# trawlers fishing" 1.0 0 -5825686 true "" "plot count trawlers with [ willFish = true ]"

SWITCH
5
700
140
733
ecologyOnly
ecologyOnly
1
1
-1000

TEXTBOX
320
425
370
443
Memory
11
0.0
1

SLIDER
10
130
185
163
coastal-fisher
coastal-fisher
0
100
45.0
5
1
NIL
HORIZONTAL

PLOT
530
340
775
482
Stock in Region A
NIL
NIL
0.0
10.0
0.0
110500.0
true
true
"" ""
PENS
"stockA" 1.0 0 -11221820 true "" "if (ticks > 0) [ plot stockA ]"
"MSY" 1.0 0 -2674135 true "" "if (ticks > 0) [ plot MSY-STOCK-A ]"

MONITOR
530
485
622
530
# out fishing
count turtles with [ willFish = true ]
17
1
11

MONITOR
625
485
705
530
# not fishing
count turtles with [ willFish = false ]
17
1
11

SLIDER
10
315
185
348
fuel-subsidy
fuel-subsidy
0
1
0.0
0.05
1
NIL
HORIZONTAL

SWITCH
5
740
175
773
fisherAtMaxCatch
fisherAtMaxCatch
1
1
-1000

CHOOSER
10
501
165
546
init-stock-size
init-stock-size
"random" "carryingCap" "halfCarryingCap" "quartCarryingCap"
2

MONITOR
700
485
775
530
alreadyAtSea
count fishers with [ goneFishing = true ]
17
1
11

SLIDER
10
570
165
603
repr4All
repr4All
0
1
1.0
0.1
1
NIL
HORIZONTAL

CHOOSER
11
439
164
484
spatial-representation
spatial-representation
"baseline-no-hotspots" "hotspots-60-40-0"
1

SLIDER
200
480
365
513
memory-time-length
memory-time-length
1
375
365.0
7
1
NIL
HORIZONTAL

SLIDER
212
707
352
740
fish-price
fish-price
1
10
1.0
0.5
1
NIL
HORIZONTAL

CHOOSER
10
205
185
250
socialInfluence
socialInfluence
"none" "descriptiveNorm" "expertise"
2

MONITOR
780
485
860
530
badWeather?
badWeather
17
1
11

SLIDER
10
355
185
388
bad-weather-probability
bad-weather-probability
0
1
0.1
0.1
1
NIL
HORIZONTAL

TEXTBOX
200
410
350
431
Fisher agents
17
0.0
1

PLOT
530
195
775
335
Stock in region B
NIL
NIL
0.0
10.0
0.0
220840.0
true
true
"" ""
PENS
"stockB" 1.0 0 -13791810 true "" "if (ticks > 0) [ plot stockB ]"
"MSY" 1.0 0 -2674135 true "" "plot MSY-STOCK-B"

SWITCH
195
10
285
43
layout
layout
0
1
-1000

SLIDER
10
55
182
88
end-of-sim-in-years
end-of-sim-in-years
0
50
25.0
1
1
NIL
HORIZONTAL

SLIDER
10
95
187
128
archipelago-fisher
archipelago-fisher
0
250
0.0
1
1
NIL
HORIZONTAL

MONITOR
950
485
1035
530
meanCatch
precision (mean [ catch ] of fishers) 2
17
1
11

MONITOR
865
535
965
580
goodSpotHitters
numFishersWgoodSpot
17
1
11

MONITOR
965
535
1102
580
goodSpotHittersPerc
precision percFishersWgoodSpot 2
17
1
11

MONITOR
865
485
950
530
catchBtickly
catchBtickly
17
1
11

PLOT
780
45
1040
190
Profit (mean per year)
NIL
NIL
0.0
10.0
0.0
1.0
true
true
"" ""
PENS
"archipelagos" 1.0 0 -13840069 true "" "if any? archipelagos [ plot mean [ accumProfitThisYear ] of archipelagos]"
"coastals" 1.0 0 -1184463 true "" "if any? coastals [ plot mean [ accumProfitThisYear ] of coastals ]"
"trawlers" 1.0 0 -5825686 true "" "if any? trawlers [ plot mean [ accumProfitThisYear ] of trawlers ]"
"Zero-line" 1.0 2 -3026479 false "" "plot 0"

PLOT
1045
45
1290
190
Satisfaction fishers
NIL
NIL
0.0
1.0
0.0
1.0
true
true
"" ""
PENS
"archipelago" 1.0 0 -13840069 true "" "if any? archipelagos [ plot mean [ satisfaction ] of archipelagos]"
"coastals" 1.0 0 -1184463 true "" "if any? coastals [ plot mean [ satisfaction ] of coastals]"
"trawlers" 1.0 0 -5825686 true "" "if any? trawlers [ plot mean [ satisfaction ] of trawlers]"

SLIDER
200
570
365
603
home-satisf-threshold
home-satisf-threshold
0
1
0.5
0.1
1
NIL
HORIZONTAL

TEXTBOX
320
555
380
573
Coastals
11
0.0
1

PLOT
780
195
1040
335
Catch (accumulated per year)
NIL
NIL
0.0
10.0
0.0
10.0
true
true
"" ""
PENS
"archipelagos" 1.0 0 -13840069 true "" "if any? archipelagos [ plot sum [ accumCatchThisYear ] of archipelagos]"
"coastals" 1.0 0 -1184463 true "" "if any? coastals [ plot sum [ accumCatchThisYear ] of coastals]"
"trawlers" 1.0 0 -5825686 true "" "if any? trawlers [ plot sum [ accumCatchThisYear ] of trawlers]"
"total" 1.0 2 -7500403 false "" "plot accumCatchYearly"

MONITOR
530
535
617
580
num fishers
count fishers
17
1
11

TEXTBOX
10
675
160
693
Sensitivity controls
14
0.0
1

MONITOR
625
535
740
580
accumCatchYearly
accumCatchYearly
17
1
11

MONITOR
740
535
862
580
NIL
accumProfitYearly
17
1
11

PLOT
1045
195
1290
335
Profit (accumulated per year)
NIL
NIL
0.0
10.0
0.0
10.0
true
true
"" ""
PENS
"trawlers" 1.0 2 -5825686 true "" "if any? trawlers [ plot sum [ accumProfitThisYear ] of trawlers]"
"archipelago" 1.0 0 -13840069 true "" "if any? archipelagos [ plot sum [ accumProfitThisYear ] of archipelagos ]"
"coastal" 1.0 0 -1184463 true "" "if any? coastals [ plot sum [ accumProfitThisYear ] of coastals]"
"total" 1.0 2 -7500403 true "" "plot accumProfitYearly"

PLOT
1045
340
1290
480
Not fishing reasons
NIL
NIL
0.0
10.0
0.0
30.0
true
true
"" ""
PENS
"#scarity" 1.0 0 -2674135 true "" "plot numThinkFishIsScarce"
"#doneEnough" 1.0 0 -955883 true "" "plot numSatisfied"
"#lowCap" 1.0 0 -6459832 true "" "plot numLowCapital"

SLIDER
10
780
182
813
sd-carcap
sd-carcap
0
1
0.0
0.1
1
NIL
HORIZONTAL

@#$#@#$#@
## WHAT IS IT?

(a general understanding of what the model is trying to show or explain)

FIBE represents a simple fishery model. Fish that reproduce and fisher with different fishing styles that fish as their main source of income. The aim of the model is to reflect the different fishing behaviours as described and observed in the (Swedish) Baltic Sea fishery and explore the consequences of different approximations of human/fisher behaviour in under different environmental and managerial scenarios.

The overarching aim is to advance the incorporation and understanding of human behaviour (diversity) in fisheries research and management. In particular focusing on insights from social (fishery) science of fisher behaviour.

## HOW IT WORKS

(what rules the agents use to create the overall behavior of the model)
Depending on the fishing style the fisher agents represent they fish differently given their motivation and fishing practise:

  * A **trawler** fisher agent only goes fishing if it expects an economic return. This means that the expected catch should at least cover the operating costs for the trawler fisher agent to decide to go out and fish. At sea, it bases its catch expectation on the fish it can perceive nearby (e.g. using sonar technology in the real-world). 

  * A **coastal** fisher agent decides to go fishing when the trade-off between expected profit and time not spent at home is not too big. This means that if a coastal fisher agent has satisfied its preference for staying home and expects a profit, it will go out fishing. Coastal fisher agents stay at home when staying home preference is not satisfied or they expect no profit. 

  * An **archipelago** fisher agent goes out fishing when it needs to, i.e. when it has not caught enough in the previous week or in the situation of having negative capital. In addition, if the archipelago fisher thinks the fish is scarce, it can decide against fishing and instead reduce living expenses. 


## HOW TO USE IT

(how to use the model, including a description of each of the items in the Interface tab)
Set the basics:

  * end-of-sim-in-years: for the duration of the simulation. _Default = 25_ (in years, a tick is a day) 
  * Number of agents:
    * archipelago-fisher: for the archipelago agents.
    * coastal-fisher: for the coastal agents.
    * offshore-trawler-fisher: for the trawler agents 

Environment settings:

  * spatial-representation: to indicates whether the fish are equally distributed or resided in er density hotspots. _Default = hotspots_
  * init-stock-size: To indicate the initial stocksize Set it to a quarter, half or full carrying capacity. _Default = half carrying capacity_.
  * repr4All: to set the reproduction rate of the fish._Default = 1_.


Fisher agent settings:

  * socialInfluence:affects the way the trawler and coastal select where to fish, based on social information. _Default = expertise_
  * home-satisf-threshold = Satisfaction threshold for the coastal agents. _Default = 0.5_
  * memory-time-length: memory over time. _Default = 365_
  * memory-spatial-length: spatial memory. _Default = 20_

Scenario settings

  * fuel-subsidy: whether (0) and height of a fuel subsity.
  * bad-weather-probability: probability that there is bad weather, this affects the archipelago and coastal agents. _Default =  0.1_


## THINGS TO NOTICE
(suggested things for the user to notice while running the model)



## THINGS TO TRY

(suggested things for the user to try to do (move sliders, switches, etc.) with the model)

## EXTENDING THE MODEL

(suggested things to add or change in the Code tab to make the model more complicated, detailed, accurate, etc.)

## NETLOGO FEATURES

(interesting or unusual features of NetLogo that the model uses, particularly in the Code tab; or where workarounds were needed for missing features)

## RELATED MODELS

(models in the NetLogo Models Library and elsewhere which are of related interest)

## CREDITS AND REFERENCES

(a reference to the model's URL on the web if it has one, as well as any other necessary credits, citations, and links)
@#$#@#$#@
default
true
0
Polygon -7500403 true true 150 5 40 250 150 205 260 250

airplane
true
0
Polygon -7500403 true true 150 0 135 15 120 60 120 105 15 165 15 195 120 180 135 240 105 270 120 285 150 270 180 285 210 270 165 240 180 180 285 195 285 165 180 105 180 60 165 15

arrow
true
0
Polygon -7500403 true true 150 0 0 150 105 150 105 293 195 293 195 150 300 150

boat
false
0
Polygon -1 true false 63 162 90 207 223 207 290 162
Rectangle -6459832 true false 150 32 157 162
Polygon -13345367 true false 150 34 131 49 145 47 147 48 149 49
Polygon -7500403 true true 158 33 230 157 182 150 169 151 157 156
Polygon -7500403 true true 149 55 88 143 103 139 111 136 117 139 126 145 130 147 139 147 146 146 149 55

boat 2
false
0
Polygon -1 true false 63 162 90 207 223 207 290 162
Rectangle -6459832 true false 150 32 157 162
Polygon -13345367 true false 150 34 131 49 145 47 147 48 149 49
Polygon -7500403 true true 157 54 175 79 174 96 185 102 178 112 194 124 196 131 190 139 192 146 211 151 216 154 157 154
Polygon -7500403 true true 150 74 146 91 139 99 143 114 141 123 137 126 131 129 132 139 142 136 126 142 119 147 148 147

boat 3
false
0
Polygon -1 true false 63 162 90 207 223 207 290 162
Rectangle -6459832 true false 150 32 157 162
Polygon -13345367 true false 150 34 131 49 145 47 147 48 149 49
Polygon -7500403 true true 158 37 172 45 188 59 202 79 217 109 220 130 218 147 204 156 158 156 161 142 170 123 170 102 169 88 165 62
Polygon -7500403 true true 149 66 142 78 139 96 141 111 146 139 148 147 110 147 113 131 118 106 126 71

boat top
true
0
Polygon -7500403 true true 150 1 137 18 123 46 110 87 102 150 106 208 114 258 123 286 175 287 183 258 193 209 198 150 191 87 178 46 163 17
Rectangle -16777216 false false 129 92 170 178
Rectangle -16777216 false false 120 63 180 93
Rectangle -7500403 true true 133 89 165 165
Polygon -11221820 true false 150 60 105 105 150 90 195 105
Polygon -16777216 false false 150 60 105 105 150 90 195 105
Rectangle -16777216 false false 135 178 165 262
Polygon -16777216 false false 134 262 144 286 158 286 166 262
Line -16777216 false 129 149 171 149
Line -16777216 false 166 262 188 252
Line -16777216 false 134 262 112 252
Line -16777216 false 150 2 149 62

box
false
0
Polygon -7500403 true true 150 285 285 225 285 75 150 135
Polygon -7500403 true true 150 135 15 75 150 15 285 75
Polygon -7500403 true true 15 75 15 225 150 285 150 135
Line -16777216 false 150 285 150 135
Line -16777216 false 150 135 15 75
Line -16777216 false 150 135 285 75

bug
true
0
Circle -7500403 true true 96 182 108
Circle -7500403 true true 110 127 80
Circle -7500403 true true 110 75 80
Line -7500403 true 150 100 80 30
Line -7500403 true 150 100 220 30

butterfly
true
0
Polygon -7500403 true true 150 165 209 199 225 225 225 255 195 270 165 255 150 240
Polygon -7500403 true true 150 165 89 198 75 225 75 255 105 270 135 255 150 240
Polygon -7500403 true true 139 148 100 105 55 90 25 90 10 105 10 135 25 180 40 195 85 194 139 163
Polygon -7500403 true true 162 150 200 105 245 90 275 90 290 105 290 135 275 180 260 195 215 195 162 165
Polygon -16777216 true false 150 255 135 225 120 150 135 120 150 105 165 120 180 150 165 225
Circle -16777216 true false 135 90 30
Line -16777216 false 150 105 195 60
Line -16777216 false 150 105 105 60

car
false
0
Polygon -7500403 true true 300 180 279 164 261 144 240 135 226 132 213 106 203 84 185 63 159 50 135 50 75 60 0 150 0 165 0 225 300 225 300 180
Circle -16777216 true false 180 180 90
Circle -16777216 true false 30 180 90
Polygon -16777216 true false 162 80 132 78 134 135 209 135 194 105 189 96 180 89
Circle -7500403 true true 47 195 58
Circle -7500403 true true 195 195 58

circle
false
0
Circle -7500403 true true 0 0 300

circle 2
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240

cow
false
0
Polygon -7500403 true true 200 193 197 249 179 249 177 196 166 187 140 189 93 191 78 179 72 211 49 209 48 181 37 149 25 120 25 89 45 72 103 84 179 75 198 76 252 64 272 81 293 103 285 121 255 121 242 118 224 167
Polygon -7500403 true true 73 210 86 251 62 249 48 208
Polygon -7500403 true true 25 114 16 195 9 204 23 213 25 200 39 123

cylinder
false
0
Circle -7500403 true true 0 0 300

dot
false
0
Circle -7500403 true true 90 90 120

face happy
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 255 90 239 62 213 47 191 67 179 90 203 109 218 150 225 192 218 210 203 227 181 251 194 236 217 212 240

face neutral
false
0
Circle -7500403 true true 8 7 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Rectangle -16777216 true false 60 195 240 225

face sad
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 168 90 184 62 210 47 232 67 244 90 220 109 205 150 198 192 205 210 220 227 242 251 229 236 206 212 183

fish
false
0
Polygon -1 true false 44 131 21 87 15 86 0 120 15 150 0 180 13 214 20 212 45 166
Polygon -1 true false 135 195 119 235 95 218 76 210 46 204 60 165
Polygon -1 true false 75 45 83 77 71 103 86 114 166 78 135 60
Polygon -7500403 true true 30 136 151 77 226 81 280 119 292 146 292 160 287 170 270 195 195 210 151 212 30 166
Circle -16777216 true false 215 106 30

fish 3
false
0
Polygon -7500403 true true 137 105 124 83 103 76 77 75 53 104 47 136
Polygon -7500403 true true 226 194 223 229 207 243 178 237 169 203 167 175
Polygon -7500403 true true 137 195 124 217 103 224 77 225 53 196 47 164
Polygon -7500403 true true 40 123 32 109 16 108 0 130 0 151 7 182 23 190 40 179 47 145
Polygon -7500403 true true 45 120 90 105 195 90 275 120 294 152 285 165 293 171 270 195 210 210 150 210 45 180
Circle -1184463 true false 244 128 26
Circle -16777216 true false 248 135 14
Line -16777216 false 48 121 133 96
Line -16777216 false 48 179 133 204
Polygon -7500403 true true 241 106 241 77 217 71 190 75 167 99 182 125
Line -16777216 false 226 102 158 95
Line -16777216 false 171 208 225 205
Polygon -1 true false 252 111 232 103 213 132 210 165 223 193 229 204 247 201 237 170 236 137
Polygon -1 true false 135 98 140 137 135 204 154 210 167 209 170 176 160 156 163 126 171 117 156 96
Polygon -16777216 true false 192 117 171 118 162 126 158 148 160 165 168 175 188 183 211 186 217 185 206 181 172 171 164 156 166 133 174 121
Polygon -1 true false 40 121 46 147 42 163 37 179 56 178 65 159 67 128 59 116

flag
false
0
Rectangle -7500403 true true 60 15 75 300
Polygon -7500403 true true 90 150 270 90 90 30
Line -7500403 true 75 135 90 135
Line -7500403 true 75 45 90 45

flower
false
0
Polygon -10899396 true false 135 120 165 165 180 210 180 240 150 300 165 300 195 240 195 195 165 135
Circle -7500403 true true 85 132 38
Circle -7500403 true true 130 147 38
Circle -7500403 true true 192 85 38
Circle -7500403 true true 85 40 38
Circle -7500403 true true 177 40 38
Circle -7500403 true true 177 132 38
Circle -7500403 true true 70 85 38
Circle -7500403 true true 130 25 38
Circle -7500403 true true 96 51 108
Circle -16777216 true false 113 68 74
Polygon -10899396 true false 189 233 219 188 249 173 279 188 234 218
Polygon -10899396 true false 180 255 150 210 105 210 75 240 135 240

house
false
0
Rectangle -7500403 true true 45 120 255 285
Rectangle -16777216 true false 120 210 180 285
Polygon -7500403 true true 15 120 150 15 285 120
Line -16777216 false 30 120 270 120

leaf
false
0
Polygon -7500403 true true 150 210 135 195 120 210 60 210 30 195 60 180 60 165 15 135 30 120 15 105 40 104 45 90 60 90 90 105 105 120 120 120 105 60 120 60 135 30 150 15 165 30 180 60 195 60 180 120 195 120 210 105 240 90 255 90 263 104 285 105 270 120 285 135 240 165 240 180 270 195 240 210 180 210 165 195
Polygon -7500403 true true 135 195 135 240 120 255 105 255 105 285 135 285 165 240 165 195

line
true
0
Line -7500403 true 150 0 150 300

line half
true
0
Line -7500403 true 150 0 150 150

pentagon
false
0
Polygon -7500403 true true 150 15 15 120 60 285 240 285 285 120

person
false
0
Circle -7500403 true true 110 5 80
Polygon -7500403 true true 105 90 120 195 90 285 105 300 135 300 150 225 165 300 195 300 210 285 180 195 195 90
Rectangle -7500403 true true 127 79 172 94
Polygon -7500403 true true 195 90 240 150 225 180 165 105
Polygon -7500403 true true 105 90 60 150 75 180 135 105

plant
false
0
Rectangle -7500403 true true 135 90 165 300
Polygon -7500403 true true 135 255 90 210 45 195 75 255 135 285
Polygon -7500403 true true 165 255 210 210 255 195 225 255 165 285
Polygon -7500403 true true 135 180 90 135 45 120 75 180 135 210
Polygon -7500403 true true 165 180 165 210 225 180 255 120 210 135
Polygon -7500403 true true 135 105 90 60 45 45 75 105 135 135
Polygon -7500403 true true 165 105 165 135 225 105 255 45 210 60
Polygon -7500403 true true 135 90 120 45 150 15 180 45 165 90

sheep
false
15
Circle -1 true true 203 65 88
Circle -1 true true 70 65 162
Circle -1 true true 150 105 120
Polygon -7500403 true false 218 120 240 165 255 165 278 120
Circle -7500403 true false 214 72 67
Rectangle -1 true true 164 223 179 298
Polygon -1 true true 45 285 30 285 30 240 15 195 45 210
Circle -1 true true 3 83 150
Rectangle -1 true true 65 221 80 296
Polygon -1 true true 195 285 210 285 210 240 240 210 195 210
Polygon -7500403 true false 276 85 285 105 302 99 294 83
Polygon -7500403 true false 219 85 210 105 193 99 201 83

square
false
0
Rectangle -7500403 true true 30 30 270 270

square 2
false
0
Rectangle -7500403 true true 30 30 270 270
Rectangle -16777216 true false 60 60 240 240

star
false
0
Polygon -7500403 true true 151 1 185 108 298 108 207 175 242 282 151 216 59 282 94 175 3 108 116 108

target
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240
Circle -7500403 true true 60 60 180
Circle -16777216 true false 90 90 120
Circle -7500403 true true 120 120 60

tree
false
0
Circle -7500403 true true 118 3 94
Rectangle -6459832 true false 120 195 180 300
Circle -7500403 true true 65 21 108
Circle -7500403 true true 116 41 127
Circle -7500403 true true 45 90 120
Circle -7500403 true true 104 74 152

triangle
false
0
Polygon -7500403 true true 150 30 15 255 285 255

triangle 2
false
0
Polygon -7500403 true true 150 30 15 255 285 255
Polygon -16777216 true false 151 99 225 223 75 224

truck
false
0
Rectangle -7500403 true true 4 45 195 187
Polygon -7500403 true true 296 193 296 150 259 134 244 104 208 104 207 194
Rectangle -1 true false 195 60 195 105
Polygon -16777216 true false 238 112 252 141 219 141 218 112
Circle -16777216 true false 234 174 42
Rectangle -7500403 true true 181 185 214 194
Circle -16777216 true false 144 174 42
Circle -16777216 true false 24 174 42
Circle -7500403 false true 24 174 42
Circle -7500403 false true 144 174 42
Circle -7500403 false true 234 174 42

turtle
true
0
Polygon -10899396 true false 215 204 240 233 246 254 228 266 215 252 193 210
Polygon -10899396 true false 195 90 225 75 245 75 260 89 269 108 261 124 240 105 225 105 210 105
Polygon -10899396 true false 105 90 75 75 55 75 40 89 31 108 39 124 60 105 75 105 90 105
Polygon -10899396 true false 132 85 134 64 107 51 108 17 150 2 192 18 192 52 169 65 172 87
Polygon -10899396 true false 85 204 60 233 54 254 72 266 85 252 107 210
Polygon -7500403 true true 119 75 179 75 209 101 224 135 220 225 175 261 128 261 81 224 74 135 88 99

wheel
false
0
Circle -7500403 true true 3 3 294
Circle -16777216 true false 30 30 240
Line -7500403 true 150 285 150 15
Line -7500403 true 15 150 285 150
Circle -7500403 true true 120 120 60
Line -7500403 true 216 40 79 269
Line -7500403 true 40 84 269 221
Line -7500403 true 40 216 269 79
Line -7500403 true 84 40 221 269

wolf
false
0
Polygon -16777216 true false 253 133 245 131 245 133
Polygon -7500403 true true 2 194 13 197 30 191 38 193 38 205 20 226 20 257 27 265 38 266 40 260 31 253 31 230 60 206 68 198 75 209 66 228 65 243 82 261 84 268 100 267 103 261 77 239 79 231 100 207 98 196 119 201 143 202 160 195 166 210 172 213 173 238 167 251 160 248 154 265 169 264 178 247 186 240 198 260 200 271 217 271 219 262 207 258 195 230 192 198 210 184 227 164 242 144 259 145 284 151 277 141 293 140 299 134 297 127 273 119 270 105
Polygon -7500403 true true -1 195 14 180 36 166 40 153 53 140 82 131 134 133 159 126 188 115 227 108 236 102 238 98 268 86 269 92 281 87 269 103 269 113

x
false
0
Polygon -7500403 true true 270 75 225 30 30 225 75 270
Polygon -7500403 true true 30 75 75 30 270 225 225 270
@#$#@#$#@
NetLogo 6.1.1
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
<experiments>
  <experiment name="expQsArchipelago-simple" repetitions="500" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <metric>runnr</metric>
    <metric>stockA</metric>
    <metric>accumCatchYearly</metric>
    <metric>accumProfitYearly</metric>
    <metric>fisherSatisfactionMean</metric>
    <metric>fisherSatisfactionSD</metric>
    <enumeratedValueSet variable="end-of-sim-in-years">
      <value value="25"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="spatial-representation">
      <value value="&quot;hotspots-60-40-0&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="init-stock-size">
      <value value="&quot;halfCarryingCap&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="offshore-trawler-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="coastal-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="archipelago-fisher">
      <value value="30"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fuel-subsidy">
      <value value="0"/>
      <value value="0.25"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="socialInfluence">
      <value value="&quot;none&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="bad-weather-probability">
      <value value="0.1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-spatial-length">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-time-length">
      <value value="365"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ecologyOnly">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fish-price">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="repr4All">
      <value value="1"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="expQsTrawler-simple" repetitions="500" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <metric>runnr</metric>
    <metric>stockB</metric>
    <metric>stockC</metric>
    <metric>stockD</metric>
    <metric>accumCatchYearly</metric>
    <metric>accumProfitYearly</metric>
    <metric>fisherSatisfactionMean</metric>
    <metric>fisherSatisfactionSD</metric>
    <enumeratedValueSet variable="end-of-sim-in-years">
      <value value="25"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="spatial-representation">
      <value value="&quot;hotspots-60-40-0&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="init-stock-size">
      <value value="&quot;halfCarryingCap&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="offshore-trawler-fisher">
      <value value="30"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="coastal-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="archipelago-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fuel-subsidy">
      <value value="0"/>
      <value value="0.25"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="socialInfluence">
      <value value="&quot;expertise&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="bad-weather-probability">
      <value value="0.1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-spatial-length">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-time-length">
      <value value="365"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ecologyOnly">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fish-price">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="repr4All">
      <value value="1"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="expQsCoastal-simple" repetitions="500" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <metric>stockA</metric>
    <metric>runnr</metric>
    <metric>stockB</metric>
    <metric>accumCatchYearly</metric>
    <metric>accumProfitYearly</metric>
    <metric>fisherSatisfactionMean</metric>
    <metric>fisherSatisfactionSD</metric>
    <enumeratedValueSet variable="end-of-sim-in-years">
      <value value="25"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="spatial-representation">
      <value value="&quot;hotspots-60-40-0&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="init-stock-size">
      <value value="&quot;halfCarryingCap&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="offshore-trawler-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="coastal-fisher">
      <value value="45"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="archipelago-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fuel-subsidy">
      <value value="0"/>
      <value value="0.25"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="socialInfluence">
      <value value="&quot;expertise&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="home-satisf-threshold">
      <value value="0.5"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="bad-weather-probability">
      <value value="0.1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-spatial-length">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-time-length">
      <value value="365"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ecologyOnly">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fish-price">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="repr4All">
      <value value="1"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="whyNotArchipelagosTickly" repetitions="100" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <metric>stockA</metric>
    <metric>catchMean</metric>
    <metric>notFishing</metric>
    <metric>numLayingLow</metric>
    <metric>numThinkFishIsScarce</metric>
    <metric>numSatisfied</metric>
    <metric>numLowCapital</metric>
    <metric>badWeather</metric>
    <enumeratedValueSet variable="manual-output">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="end-of-sim">
      <value value="9125"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="init-stock-size">
      <value value="&quot;halfCarryingCap&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="archipelago-fisher">
      <value value="30"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="bad-weather-probability">
      <value value="0.1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="init-knowledge-distr">
      <value value="&quot;fishingStyle&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="socialInfluence">
      <value value="&quot;none&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fuel-subsidy">
      <value value="0"/>
      <value value="0.25"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-time-length">
      <value value="365"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-spatial-length">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="coastal-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="offshore-trawler-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="repr4All">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ecologyOnly">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="repr4All?">
      <value value="true"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="count-visits">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fish-price">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="env_scenario">
      <value value="&quot;hotspot-constant&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="spatial-representation">
      <value value="&quot;hotspots&quot;"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="whyNotCoastalsTickly" repetitions="100" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <metric>stockA</metric>
    <metric>stockB</metric>
    <metric>catchMean</metric>
    <metric>notFishing</metric>
    <metric>badWeather</metric>
    <metric>numFishersWgoodSpot</metric>
    <metric>percFishersWgoodSpot</metric>
    <metric>numExpectNoProfit</metric>
    <metric>numWantToBeHome</metric>
    <enumeratedValueSet variable="manual-output">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="end-of-sim">
      <value value="9125"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="init-stock-size">
      <value value="&quot;halfCarryingCap&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="archipelago-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="coastal-fisher">
      <value value="45"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="offshore-trawler-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="bad-weather-probability">
      <value value="0.1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="init-knowledge-distr">
      <value value="&quot;fishingStyle&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="socialInfluence">
      <value value="&quot;expertise&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fuel-subsidy">
      <value value="0"/>
      <value value="0.25"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-time-length">
      <value value="365"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-spatial-length">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="repr4All">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ecologyOnly">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="repr4All?">
      <value value="true"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="count-visits">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fish-price">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="env_scenario">
      <value value="&quot;hotspot-constant&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="spatial-representation">
      <value value="&quot;hotspots&quot;"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="whyNotTrawlerTickly" repetitions="100" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <metric>stockB</metric>
    <metric>stockC</metric>
    <metric>stockD</metric>
    <metric>catchMean</metric>
    <metric>notFishing</metric>
    <metric>numExpectNoProfit</metric>
    <enumeratedValueSet variable="manual-output">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="end-of-sim">
      <value value="9125"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="init-stock-size">
      <value value="&quot;halfCarryingCap&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="archipelago-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="coastal-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="offshore-trawler-fisher">
      <value value="30"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="bad-weather-probability">
      <value value="0.1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="init-knowledge-distr">
      <value value="&quot;fishingStyle&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="socialInfluence">
      <value value="&quot;expertise&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fuel-subsidy">
      <value value="0"/>
      <value value="0.25"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-time-length">
      <value value="365"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-spatial-length">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="repr4All">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ecologyOnly">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="repr4All?">
      <value value="true"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="count-visits">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fish-price">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="env_scenario">
      <value value="&quot;hotspot-constant&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="spatial-representation">
      <value value="&quot;hotspots&quot;"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="expQsArchipelago-FuelSubs" repetitions="250" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <metric>runnr</metric>
    <metric>stockA</metric>
    <metric>accumCatchYearly</metric>
    <metric>accumProfitYearly</metric>
    <metric>fisherSatisfactionMean</metric>
    <metric>fisherSatisfactionSD</metric>
    <enumeratedValueSet variable="end-of-sim-in-years">
      <value value="25"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="spatial-representation">
      <value value="&quot;hotspots-60-40-0&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="init-stock-size">
      <value value="&quot;halfCarryingCap&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="offshore-trawler-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="coastal-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="archipelago-fisher">
      <value value="30"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fuel-subsidy">
      <value value="0"/>
      <value value="0.25"/>
      <value value="0.5"/>
      <value value="0.75"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="socialInfluence">
      <value value="&quot;none&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="bad-weather-probability">
      <value value="0.1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-spatial-length">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-time-length">
      <value value="365"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ecologyOnly">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fish-price">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="repr4All">
      <value value="1"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="expQsCoastal-FuelSubs" repetitions="250" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <metric>stockA</metric>
    <metric>runnr</metric>
    <metric>stockB</metric>
    <metric>accumCatchYearly</metric>
    <metric>accumProfitYearly</metric>
    <metric>fisherSatisfactionMean</metric>
    <metric>fisherSatisfactionSD</metric>
    <enumeratedValueSet variable="end-of-sim-in-years">
      <value value="25"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="spatial-representation">
      <value value="&quot;hotspots-60-40-0&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="init-stock-size">
      <value value="&quot;halfCarryingCap&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="offshore-trawler-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="coastal-fisher">
      <value value="45"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="archipelago-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fuel-subsidy">
      <value value="0"/>
      <value value="0.25"/>
      <value value="0.5"/>
      <value value="0.7"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="socialInfluence">
      <value value="&quot;expertise&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="home-satisf-threshold">
      <value value="0.5"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="bad-weather-probability">
      <value value="0.1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-spatial-length">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-time-length">
      <value value="365"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ecologyOnly">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fish-price">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="repr4All">
      <value value="1"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="expQsTrawler-FuelSubs" repetitions="250" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <metric>runnr</metric>
    <metric>stockB</metric>
    <metric>stockC</metric>
    <metric>stockD</metric>
    <metric>accumCatchYearly</metric>
    <metric>accumProfitYearly</metric>
    <metric>fisherSatisfactionMean</metric>
    <metric>fisherSatisfactionSD</metric>
    <enumeratedValueSet variable="end-of-sim-in-years">
      <value value="25"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="spatial-representation">
      <value value="&quot;hotspots-60-40-0&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="init-stock-size">
      <value value="&quot;halfCarryingCap&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="offshore-trawler-fisher">
      <value value="36"/>
      <value value="10"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="coastal-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="archipelago-fisher">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fuel-subsidy">
      <value value="0"/>
      <value value="0.25"/>
      <value value="0.5"/>
      <value value="0.75"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="socialInfluence">
      <value value="&quot;expertise&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="bad-weather-probability">
      <value value="0.1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-spatial-length">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="memory-time-length">
      <value value="365"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ecologyOnly">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="fish-price">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="repr4All">
      <value value="1"/>
    </enumeratedValueSet>
  </experiment>
</experiments>
@#$#@#$#@
@#$#@#$#@
default
0.0
-0.2 0 0.0 1.0
0.0 1 1.0 0.0
0.2 0 0.0 1.0
link direction
true
0
Line -7500403 true 150 150 90 180
Line -7500403 true 150 150 210 180
@#$#@#$#@
1
@#$#@#$#@
