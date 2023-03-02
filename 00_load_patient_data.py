import json
from neo4j import GraphDatabase

"""
This script will load synthea patient data
"""
with open("config.json") as f:
    config = json.load(f)

port = config["port"]
url = "neo4j+s://neo4j-patientjourney.graphdatabase.ninja:" + port
user = config["user"]
pswd = config["pswd"]
importFolder = config["import_Folder"]

folderName = "csv"
#datasetSize = ""
datasetSize = "100k"


driver = GraphDatabase.driver(url, auth=(user, pswd))
neo4j = driver.session()

"""
Load constraints
"""
constraints = [
    "CREATE CONSTRAINT patientNumber IF NOT EXISTS for (n:Patient) REQUIRE n.id is UNIQUE",
    "CREATE CONSTRAINT observation IF NOT EXISTS for (n:Observation) REQUIRE n.code is UNIQUE",
    "CREATE CONSTRAINT organization IF NOT EXISTS for (n:Organization) REQUIRE n.id is UNIQUE",
    "CREATE CONSTRAINT drug IF NOT EXISTS for (n:Drug) REQUIRE n.code is UNIQUE",
    "CREATE CONSTRAINT careplan IF NOT EXISTS for (n:CarePlan) REQUIRE n.id is UNIQUE",
    "CREATE CONSTRAINT reaction IF NOT EXISTS for (n:Reaction) REQUIRE n.id is UNIQUE",
    "CREATE CONSTRAINT device IF NOT EXISTS for (n:Device) REQUIRE n.code is UNIQUE",
    "CREATE CONSTRAINT speciality IF NOT EXISTS for (n:Speciality) REQUIRE n.name is UNIQUE"]

pointIndexes = [
    "CREATE POINT INDEX patientLocation IF NOT EXISTS FOR (n:Patient) ON (n.location)",
    "CREATE POINT INDEX providerLocation IF NOT EXISTS FOR (n:Provider) ON (n.location)",
    "CREATE POINT INDEX organizationLocation IF NOT EXISTS FOR (n:Organization) ON (n.location)"]

indexes = [
    "CREATE INDEX patient_index_name IF NOT EXISTS FOR (n:Patient) ON (n.id)",
    "CREATE INDEX encounterId_name IF NOT EXISTS FOR (n:Encounter) ON (n.id)",
    "CREATE INDEX encounterDate_name IF NOT EXISTS FOR (n:Encounter) ON (n.date)",
    "CREATE INDEX encounterIsEnd_name IF NOT EXISTS FOR (n:Encounter) ON (n.isEnd)",
    "CREATE INDEX provider_name IF NOT EXISTS FOR (n:Provider) ON (n.id)",
    "CREATE INDEX payer_name IF NOT EXISTS FOR (n:Payer) ON (n.id)",
    "CREATE INDEX organization_name IF NOT EXISTS FOR (n:Organization) ON (n.id)",
    "CREATE INDEX drug_name IF NOT EXISTS FOR (n:Drug) ON (n.code)",
    "CREATE INDEX carePlan_name IF NOT EXISTS FOR (n:CarePlan) ON (n.id)",
    "CREATE INDEX speciality_name IF NOT EXISTS FOR (n:Speciality) ON (n.name)",
    "CREATE INDEX allergy_name IF NOT EXISTS FOR (n:Allergy) ON (n.code)",
    "CREATE INDEX procedure_name IF NOT EXISTS FOR (n:Procedure) ON (n.code)",
    "CREATE INDEX condition_name IF NOT EXISTS FOR (n:Condition) ON (n.code)",
    "CREATE INDEX observation_name IF NOT EXISTS FOR (n:Observation) ON (n.code)",
    "CREATE INDEX device_name IF NOT EXISTS FOR (n:Device) ON (n.code)"] 
# loading constraints and indexes
for c in constraints:
    if not c == "":
        result = neo4j.run("" + c)
# loading point indexes
for p in pointIndexes:
    if not p == "":
        result = neo4j.run("" + p)
# loading indexes
for i in indexes:
    if not i == "":
        result = neo4j.run("" + i)

patient = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/patients.csv' AS line FIELDTERMINATOR ',' return line",
    "MERGE(p:Patient{{id:line['Id']}})
    SET 
    p.first = line['FIRST'],
    p.last = line['LAST'],
    p.birthdate = Date(line['BIRTHDATE']),
    p.birthplace = line['BIRTHPLACE'],
    p.deathdate = Date(line['DEATHDATE']),
    p.ethnicity = line['ETHNICITY'],
    p.gender = line['GENDER'],
    p.prefix = line['PREFIX'],
    p.race = line['RACE'],
    p.address = line['ADDRESS'],
    p.state = line['STATE'],
    p.city = line['CITY'],
    p.county = line['COUNTY'],
    p.drivers = line['DRIVERS'],
    p.healthcare_coverage = toFloat(line['HEALTHCARE_COVERAGE']),
    p.healthcare_expenses = toFloat(line['HEALTHCARE_EXPENSES']),
    p.latitude = toFloat(line['LAT']),
    p.longitude = toFloat(line['LON']),
    p.location = point({{latitude:toFloat(line['LAT']),longitude: toFloat(line['LON'])}}),
    p.martial = line['MARITAL']",
    {{batchSize:2000, parallel:false}}
)
"""

payers = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/payers.csv' AS line FIELDTERMINATOR ',' return line",
    "MERGE (p:Payer{{id:line['Id']}})
    SET p.name = line['NAME'],
        p.address = line.line['ADDRESS'],
        p.city = line['CITY'],
        p.zip = line['ZIP'],
        p.state = line['STATE_HEADQUARTERED']",
    {{batchSize:2000, parallel:false}}
)
"""

encounters = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/encounters.csv' AS line FIELDTERMINATOR ',' return line",
    "MERGE (e:Encounter {{id:line['Id']}})
        SET e.code = line['CODE'],
        e.description = line['DESCRIPTION'],
        e.class = line['ENCOUNTERCLASS'],
        e.start = datetime(line['START']),
        e.baseCost = toFloat(line['BASE_ENCOUNTER_COST']),
        e.claimCost = toFloat(line['TOTAL_CLAIM_COST']),
        e.coveredAmount = toFloat(line['PAYER_COVERAGE']),
        e.isEnd = false,
        e.end = datetime(line['STOP'])
        MERGE (p:Patient {{id:line['PATIENT']}})
        MERGE (p)-[:HAS_ENCOUNTER]->(e)
        MERGE (pr:Provider {{id: line['PROVIDER']}})
        MERGE (e)-[:HAS_PROVIDER]->(pr)
        MERGE (o:Organization {{id:line['ORGANIZATION']}})
        MERGE (e)-[:AT_ORGANIZATION]->(o)
        WITH e,line
        MATCH (pa:Payer {{id:line['PAYER']}})
        MERGE (e)-[:HAS_PAYER]->(pa)",
        {{batchSize:2000, parallel:false}}
)
"""

providers = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/providers.csv' AS line FIELDTERMINATOR ',' return line",
    "MERGE (p:Provider {{id: line['Id']}})
        SET p.name = line['NAME'],
        p.address = line['ADDRESS'],
        p.location = point({{latitude:toFloat(line['LAT']), longitude:toFloat(line['LON'])}})
    MERGE (s:Speciality {{name: line['SPECIALITY']}})
    MERGE (p)-[:HAS_SPECIALITY]->(s)
    MERGE (o:Organization {{id: line['ORGANIZATION']}})
    MERGE (p)-[:BELONGS_TO]->(o)",        
    {{batchSize:2000, parallel:false}}
)
"""

payerTransitions = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/payer_transitions.csv' AS line FIELDTERMINATOR ',' return line",
    "MATCH (p:Patient {{id:line['PATIENT']}})
    MERGE (payer:Payer {{id:line['PAYER']}})
    CREATE (p)-[s:INSURANCE_START]->(payer)
        SET s.year=toInteger(line['START_YEAR'])
    CREATE (p)-[e:INSURANCE_END]->(payer)
        SET e.year=toInteger(line['END_YEAR'])",
    {{batchSize:2000, parallel:false}}
)    
"""

allergies = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/allergies.csv' AS line FIELDTERMINATOR ',' return line",
    "MATCH (p:Patient {{id:line['PATIENT']}})
    MERGE (a:Allergy {{code: line['CODE']}})
    SET a.description = line['DESCRIPTION'],
        a.type = line['TYPE'],
        a.category = line['CATEGORY'],
        a.system = line['SYSTEM']
    MERGE (e:Encounter {{id:line['ENCOUNTER']}})
    MERGE (p)-[:HAS_ENCOUNTER]->(e)
    MERGE (p)-[:HAS_ALLERGY]->(a)
    MERGE (e)-[r:ALLERGY_DETECTED]->(a)
    SET r.start = datetime(line['START'])
    WITH p,a,e,r,line
    WHERE line['REACTION1'] IS NOT NULL and line['REACTION1'] <> ''
    MERGE (r1:Reaction {{id: line['REACTION1']}})
        SET r1.description = line['DESCRIPTION1']
    MERGE (p)-[rr:HAS_REACTION]->(r1)
        SET rr.severity = line['SEVERITY1']
    MERGE (a)-[:CAUSES_REACTION]->(r1)
    WITH p,a,e,r,line
    WHERE line['REACTION2'] IS NOT NULL and line['REACTION2'] <> ''
    MERGE (r2:Reaction {{id: line['REACTION2']}})
        SET r2.description = line['DESCRIPTION2']
    MERGE (p)-[rrr:HAS_REACTION]->(r2)
        SET rrr.severity = line['SEVERITY2']
    MERGE (a)-[:CAUSES_REACTION]->(r2)
    WITH p,a,e,r,line
    WHERE line['STOP'] IS NOT NULL and line['STOP'] <> ''
    SET r.isEnd = True,
        r.stop = datetime(line['STOP'])",
    {{batchSize:2000, parallel:false}}
)    
"""

conditions = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/conditions.csv' AS line FIELDTERMINATOR ',' return line",
    "MATCH (p:Patient {{id:line['PATIENT']}})
        MERGE (c:Condition {{code:line['CODE']}})
            SET c.description  = line['DESCRIPTION'],
                c.start = datetime(line['START']),
                c.code = line['CODE'],
                c.isEnd = false
        MERGE (e:Encounter {{id:line['ENCOUNTER']}})
        MERGE (p)-[:HAS_ENCOUNTER]->(e)
        MERGE (e)-[:HAS_CONDITION]->(c)
        WITH p,c,e,line
            WHERE line['STOP'] IS NOT NULL and line['STOP'] <> ''
                SET c.stop = line['STOP'], c.isEnd = true",
   {{batchSize:2000, parallel:false}}
) 
"""

medications = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/medications.csv' AS line FIELDTERMINATOR ',' return line",
    "MERGE (p:Patient {{id:line['PATIENT']}})
    MERGE (e:Encounter {{id:line['ENCOUNTER']}})
    MERGE (d:Drug {{code:line['CODE']}})
        SET d.description = line['DESCRIPTION'],
            d.basecost = line['BASE_COST'],
            d.totalcost = line['TOTALCOST'],
            d.isEnd = false,
            d.start = datetime(line['START'])
    MERGE (p)-[:HAS_ENCOUNTER]->(e)
    MERGE (e)-[:HAS_DRUG]->(d)
    WITH p,d,e,line
    WHERE line['STOP'] IS NOT NULL and line['STOP'] <> ''
        SET d.stop = datetime(line['STOP']), d.isEnd = true",
    {{batchSize:2000, parallel:false}}
)   
"""

procedures = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/procedures.csv' AS line FIELDTERMINATOR ',' return line",
    "MERGE (p:Patient {{id:line['PATIENT']}})
    MERGE (r:Procedure {{code:line['CODE']}})
        SET r.description=line['DESCRIPTION']
    MERGE (pe:Encounter {{id:line['ENCOUNTER'], isEnd: false}})
        ON CREATE
        SET pe.date=datetime(line['START']), pe.code=line['CODE']
        ON MATCH
        SET pe.code=line['CODE']
    MERGE (p)-[:HAS_ENCOUNTER]->(pe)
    MERGE (pe)-[:HAS_PROCEDURE]->(r)",
    {{batchSize:2000, parallel:false}}
)
"""

observations = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/observations.csv' AS line FIELDTERMINATOR ',' return line",
    "WITH line WHERE line['ENCOUNTER'] IS NOT NULL and line['ENCOUNTER'] <> '' 
    MATCH (p:Patient {{id:line['PATIENT']}})
    MERGE (oe:Encounter {{id:line['ENCOUNTER']}})
    MERGE (ob:Observation{{code:line['CODE']}})
    SET ob.description = line['DESCRIPTION'],
            ob.type = line['TYPE'],
            ob.units = line['UNTIS'],
            ob.category = line['CATEGORY'],
            ob.type = line['TYPE']
    MERGE (oe)-[r:HAS_OBSERVATION]->(ob)
    SET r.value = line['VALUE'], 
        r.date = datetime(line['DATE']),
        r.unit = line['UNITS']",
    {{batchSize:2000, parallel:false}}
)
"""

carePlans = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/careplans.csv' AS line FIELDTERMINATOR ',' return line",
    "MATCH (p:Patient {{id:line['PATIENT']}})
    MERGE (c:CarePlan {{id:line['Id']}})
    SET c.description = line['DESCRIPTION'],
        c.reasoncode = line['REASONCODE'],
        c.code = line['CODE'],
        c.start = datetime(line['START']),
        c.isEnd = false
    MERGE (e:Encounter {{id:line['ENCOUNTER']}})
    MERGE (p)-[:HAS_ENCOUNTER]->(e)
    MERGE (e)-[:HAS_CARE_PLAN]->(c)
    WITH p,c, line
    WHERE line['STOP'] IS NOT NULL and line['STOP'] <> '' 
        SET c.end = datetime(line['STOP']),
            c.isEnd = true",
    {{batchSize:2000, parallel:false}}
)         
"""

organizations = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/organizations.csv' AS line FIELDTERMINATOR ',' return line",
    "MERGE (o:Organization {{id:line['Id']}})
        SET o.name = line['NAME'],
        o.address = line['ADDRESS'],
        o.city = line['CITY'],
        o.location = point({{latitude:toFloat(line['LAT']), longitude:toFloat(line['LON'])}})",
    {{batchSize:2000, parallel:false}}
) 
"""

devices = f"""
CALL apoc.periodic.iterate(
    "LOAD CSV WITH HEADERS FROM 'file:///{folderName}{datasetSize}/devices.csv' AS line FIELDTERMINATOR ',' return line",
    "MERGE (d:Device {{code:line['CODE']}})
        SET d.description = line['DESCRIPTION']
    MERGE (e:Encounter {{id:line['ENCOUNTER']}})
    MERGE (e)-[:DEVICE_USED]->(d)
    ",
    {{batchSize:2000, parallel:false}}
) 
"""
queries = [patient, observations,payers,encounters,providers, payerTransitions, allergies, conditions, medications,procedures,carePlans,organizations, devices]
#queries = [patient]
for count, query in enumerate(queries):
    if True:
        if not query == "":
            print(str(count))
            #print(f'{query=}'.split('=')[0])
            result = neo4j.run("" + query)
    else:
        if not query == "":
            result = neo4j.run("" + query)

bringEncountersInOrder = """
CALL apoc.periodic.iterate(
    "MATCH (p:Patient) return p",
    "MATCH (p)-[:HAS_ENCOUNTER]->(e:Encounter)
    SET e.isEnd = false
    WITH p,e ORDER BY e.start
    WITH p, collect(e) as encounters, head(reverse(collect(e))) as last, head(collect(e)) as first
    MERGE (p)-[:FIRST]->(first)
    MERGE (p)-[:LAST]->(last)
    SET last.isEnd = True,
    first.isStart = True
    WITH apoc.coll.pairsMin(encounters) as pairs
    UNWIND pairs as pair
    WITH pair[0] as start, pair[1] as end
    MERGE (start)-[:NEXT]->(end)",
    {batchSize: 100}
)
"""

conditionDrugCount = """
MATCH (c:Condition)<-[:HAS_CONDITION]-(e:Encounter)-[:HAS_DRUG]->(d:Drug)
WITH c, COUNT(*) as total_pairs
SET c.total_drug_pairings = total_pairs;
"""

conditionDescription = """
MATCH (c:Condition)
MERGE (cd:ConditionDescription {text: c.description})
"""

connectConsecutiveConditions = """
MATCH (c:Condition)<--(e:Encounter)-[:NEXT*0..1]->(e2:Encounter)-->(c2:Condition)
WITH c.description as desc1, c2.description as desc2, COUNT(*) as count
MATCH (n1:ConditionDescription{text: desc1}), (n2:ConditionDescription{text: desc2})
CREATE (n1)-[:NEXT{amount:count}]->(n2)
"""

#postprocessing = [bringEncountersInOrder]
postprocessing = [bringEncountersInOrder,conditionDrugCount, conditionDescription, connectConsecutiveConditions]
print('Postprocessing')
for count, query in enumerate(postprocessing):
    if True:
        if not query == "":
            print(str(count))
            #print(f'{query=}'.split('=')[0])
            result = neo4j.run("" + query)

neo4j.close()