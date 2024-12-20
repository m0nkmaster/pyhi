# LDBWS Documentation

![NRE Logo](images/nationalrailenquiries.gif)

## Live Departure Boards Web Service (LDBWS / OpenLDBWS)

---

### What is it?

LDBWS provides a request-response web service to access real-time train information from Darwin. This is the same information that powers the Live Departure Boards, provided in XML format.

---

### Where is it?

The latest WSDL may be found at [https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx?ver=2021-11-01](https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx?ver=2021-11-01).

The current schema version is **2021-11-01**.

The WSDL for any supported previous versions of the service can be found at: https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx?ver=yyyy-mm-dd where `yyyy-mm-dd` is replaced by the correct version number (obtained from the targetNamespace of the schema). 

Clients should always use the current version. However, developers should periodically check this page for new versions.

Note: The web service endpoint expects a SOAP XML message and cannot be accessed from a web browser.

---

### How is it accessed?

LDBWS is provided as a SOAP web service. Clients typically use an automatic proxy generation tool to interface with the web service. This tool can be pointed at the WSDL URL or use locally downloaded WSDL and XSD files.

All licensed users need a token to access public web services. The token is passed as a SOAP Header value. Requests with no token or an incorrect token will be rejected.

For operations requiring a CRS code, refer to [CRS Code List](http://www.nationalrail.co.uk/stations_destinations/48541.aspx).

#### Supported Operations

**GetArrBoardWithDetails**

- **Version:** 2015-05-14 and above.  
- **Description:** Returns all public arrivals for the supplied CRS code within a defined time window, including service details.  
- **Parameters:**  
  - `numRows` (integer, 0-10 exclusive)  
  - `crs` (string, 3 characters)  
  - `filterCrs` (string, 3 characters) - *Optional*  
  - `filterType` (string, "from" or "to") - Defaults to "to"  
  - `timeOffset` (integer, -120 to 120) - Defaults to 0  
  - `timeWindow` (integer, -120 to 120)  

- **Response:** `StationBoardWithDetails` object.

---

**GetArrDepBoardWithDetails**

- **Version:** 2015-05-14 and above.  
- **Description:** Returns all public arrivals and departures for the supplied CRS code within a defined time window, including service details.  
- **Parameters:**  
  - `numRows` (integer, 0-10 exclusive)  
  - `crs` (string, 3 characters)  
  - `filterCrs` (string, 3 characters) - *Optional*  
  - `filterType` (string, "from" or "to") - Defaults to "to"  
  - `timeOffset` (integer, -120 to 120) - Defaults to 0  
  - `timeWindow` (integer, -120 to 120)  

- **Response:** `StationBoardWithDetails` object.

---

**GetArrivalBoard**

- **Description:** Returns all public arrivals for the supplied CRS code within a defined time window.  
- **Parameters:**  
  - `numRows` (integer, 0-150 exclusive)  
  - `crs` (string, 3 characters)  
  - `filterCrs` (string, 3 characters) - *Optional*  
  - `filterType` (string, "from" or "to") - Defaults to "to"  
  - `timeOffset` (integer, -120 to 120) - Defaults to 0  
  - `timeWindow` (integer, -120 to 120)  

- **Response:** `StationBoard` object.

---

For detailed information on other operations and supported objects, refer to the complete documentation.

---

### Error Handling

Errors during execution, such as invalid parameters or service unavailability, are communicated via SOAP Faults, typically translated by client proxies into exceptions.

---

### Objects

For object details, refer to sections like:

- **CallingPoint**  
- **CoachData**  
- **DepartureItem**  
- **StationBoard**  
- **ServiceDetails**  

Each object contains attributes relevant to train services, station boards, and additional service details.