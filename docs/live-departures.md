# API Endpoints

## Endpoints

1. **GetDepartureBoard Endpoint**

/LDBWS/api/20220120/GetDepartureBoard/{crs}

2. **GetDepBoardWithDetails Endpoint**

/LDBWS/api/20220120/GetDepBoardWithDetails/{crs}

### URL

https://api1.raildata.org.uk/1010-live-departure-board-dep1_2/LDBWS/api/20220120/GetDepartureBoard/{crs}

*(This is the URL to access the API for this data product.)*

---

## Access via cURL

```bash
$ curl -v -X GET -H 'x-apikey:<apikey>' https://api1.raildata.org.uk/1010-live-departure-board-dep1_2

API Access Credentials
	•	Consumer Key: VKGezNiGkY2xt68Y09gONAyvhkzT6okGniFWAFaFn8GniLFH
	•	Consumer Secret: 1AN7qke20o38gfIhBD88yBKVUkx4m7FlQEkZ1kKUETCdGVNbnbn8wf4krmjcCmEY

Example Request

GET Request

GET https://api1.raildata.org.uk/1010-live-departure-board-dep1_2/LDBWS/api/20220120/GetDepartureBoard/LST

Headers

Header	Value
x-apikey	VKGezNiGkY2xt68Y09gONAyvhkzT6okGniFWAFaFn8GniLFH

Path Parameters

Parameter	Value
crs	LST

Query Parameters

Parameter	Value
numRows	10
filterCrs	PAD
filterType	to
timeOffset	0
timeWindow	120

Notes
	•	All requests sent to the API count towards your usage.
	•	Check the licence details for any usage charges or limits.

