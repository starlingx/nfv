====================================================
NFV VIM API v1
====================================================

Manage software deployment orchestration with the StarlingX NFV VIM API. This
includes creation, application and querying of,

* Deploy strategy(major and patch release).
* Kubernetes strategy.
* System config update strategy.
* Firmware update strategy.
* Kubernetes rootca update strategy.

Software deployment orchestration automates the process of upversioning the StarlingX
software to a new major release or new patch (In-Service or Reboot Required (RR)) release.
It automates the execution of all software deploy steps across all hosts in a cluster,
based on the configured policies.

The typical port used for the NFV VIM REST API is 4545. However, proper
technique would be to look up the nfv vim service endpoint in Keystone
response to your authentication request to get a Keystone Token.

---------------------------------
Keystone Authentication Request
---------------------------------

The majority of NFV VIM RESTAPI Requests are authenticated and require a Keystone Token.

**Note**

Create a User & Project scoped token in Keystone (typical port used for Keystone Authentication REST API is 5000).
The user must have ‘admin’ role.
The Token created will be returned in the X-Subject-Token Header of the Response.
The Token created should be used in the X-Auth-Token Header for ALL VIM NFV Requests documented in this page.

**************************************************
Create a User & Project scoped token in Keystone
**************************************************

.. rest_method:: POST /v3/auth/tokens

**Request**

**Request body parameters**

.. csv-table::
  :header: "Parameter", "Style", "Type", "Description"
  :widths: 20, 10, 10, 20

  "See example below for full structure", "", "", "Use values in example for all
  attributes except user name and password."
  "identity:password:user:name", "plain", "xsd:string", "Your user name; note that
  user must have ‘admin’ role."
  "identity:password:user:password", "plain", "xsd:string", "Your user’s password."

**Request body example**

::

          {
            "auth": {
              "identity": {
                "methods": ["password"],
                "password": {
                  "user": {
                    "name": "joetheadmin",
                    "domain": { "id": "default" },
                    "password": "joetheadminpassword"
                    }
                 }
              },
              "scope": {
                "project": {
                  "name": "admin",
                  "domain": { "id": "default" }
                }
              }
            }
          }

**Response**

**Normal header response codes**

200

**Error header response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401), forbidden (403),
badMethod (405), overLimit (413)

**Response header example**

::

          HTTP/1.1 201 CREATED
          Server: gunicorn
          Date: Fri, 13 Dec 2024 16:43:17 GMT
          Connection: keep-alive
          Content-Type: application/json
          Content-Length: 8057
          X-Subject-Token: gAAAAABnXGQlzlhAj60MKrchnA_02oW-fEJngBSKZ5xUXQsLUgGDU0x4Aol8aCOOr0ew46nYs0
          U8U0IC563o5j0xYMaBW_ZY15_V9yPqb7zI2gkpZgXJoNO-x6WiLoy5VRU5WKBfYvZaUEzdA-SeJtYHXmG5ci7n0CjgMzLX4IqybS0lp4ahiE0
          Vary: X-Auth-Token

**Response body example**

::

            {
              "token" : {
                "audit_ids" : [
                  "-3461BwAQqGzfjpFdkehJQ"
                 ],
                 "catalog" : [
                 {
                   "endpoints" : [
                   {
                     "id" : "0f055ff9208e45eb8d500ad3d1a2ebdd",
                     "interface" : "admin",
                     "region" : "SystemController",
                     "region_id" : "SystemController",
                     "url" : https://10.8.76.2:26386/v1
                   },
                   {
                     "id" : "2c65814c534444ffb3d2bba19ce86b7c",
                     "interface" : "internal",
                     "region" : "SystemController",
                     "region_id" : "SystemController",
                     "url" : http://10.8.76.2:26385/v1
                   },
                   {
                     "id" : "a6cb183c72f64f0aae0206e624a9a12b",
                     "interface" : "public",
                     "region" : "SystemController",
                     "region_id" : "SystemController",
                     "url" : http://10.8.76.2:26385/v1
                   },
                   {
                     "id" : "5f71d132c71c4f29b94876d94a7815cc",
                     "interface" : "internal",
                     "region" : "RegionOne",
                     "region_id" : "RegionOne",
                     "url" : http://10.8.76.2:6385/v1
                   },
                   {
                     "id" : "a4aae2b6f9174a38bf24ebf49b7fea0a",
                     "interface" : "public",
                     "region" : "RegionOne",
                     "region_id" : "RegionOne",
                     "url" : http://10.8.76.2:6385/v1
                   },
                   {
                     "id" : "840d59bc34fb45dba6f874b3015e2caf",
                     "interface" : "admin",
                     "region" : "RegionOne",
                     "region_id" : "RegionOne",
                     "url" : https://10.8.120.2:6386/v1
                   },
                   {
                     "id" : "ca0600a2d27e442281b0c9b46e76bb83",
                     "interface" : "admin",
                     "region" : "subcloud3",
                     "region_id" : "subcloud3",
                     "url" : https://10.8.130.2:6386/v1
                   }
                 ],
                 "id" : "aa305d9a30ac4500bf6897bfd626678b",
                 "name" : "sysinv",
                 "type" : "platform"
               },
               {
               "endpoints" : [
               {
                  "id" : "0c2db2989f1c4751ade1d411c0195b52",
                  "interface" : "internal",
                  "region" : "RegionOne",
                  "region_id" : "RegionOne",
                  "url" : http://10.8.76.2:5000
               },
               {
                  "id" : "4540cf391ac74feca7eb470f929df29b",
                  "interface" : "public",
                  "region" : "RegionOne",
                  "region_id" : "RegionOne",
                  "url" : http://10.8.176.2:5000
               },
               {
                  "id" : "a009a8cfb46e458e83e0ee84ea966aab",
                  "interface" : "internal",
                  "region" : "SystemController",
                  "region_id" : "SystemController",
                  "url" : http://10.8.76.2:25000/v3
               },
               {
                  "id" : "f9e1ba5911504efda69bc7e2bb793b5a",
                  "interface" : "public",
                  "region" : "SystemController",
                  "region_id" : "SystemController",
                  "url" : http://10.8.120.2:25000/v3
               },
               {
                  "id" : "dd8ff1e5100444f089ebc70d5a9547f7",
                  "interface" : "admin",
                  "region" : "RegionOne",
                  "region_id" : "RegionOne",
                  "url" : https://10.8.76.2:5001
               },
               {
                  "id" : "81ca75c3a5ca486a97c69649d9b265d3",
                  "interface" : "admin",
                  "region" : "SystemController",
                  "region_id" : "SystemController",
                  "url" : https://10.8.76.2:25001/v3
               },
               {
                  "id" : "d2ec214284fe4b7a9499a9bff1c5f044",
                  "interface" : "admin",
                  "region" : "subcloud3",
                  "region_id" : "subcloud3",
                  "url" : https://10.8.130.2:5001/v3
               }
             ],
             "id" : "d75a792561184e638325941c749334ac",
             "name" : "keystone",
             "type" : "identity"
             },
             ],
             "expires_at" : "2024-12-13T17:42:33.000000Z",
             "is_domain" : false,
             "issued_at" : "2024-12-13T16:42:33.000000Z",
             "methods" : [
             "password"
             ],
             "project" : {
             "domain" : {
             "id" : "default",
             "name" : "Default"
             },
             "id" : "a75f654e73394652bfbc4e4613ab0249",
             "name" : "admin"
             },
             "roles" : [
             {
             "id" : "b45c7325466f49ecb1f7bbe7fc293e2c",
             "name" : "admin"
             },
             {
             "id" : "19bbf3627d904fe8b167036bc694a04f",
             "name" : "member"
             },
             {
             "id" : "017afd0f38b745e08d0b888219288d83",
             "name" : "reader"
             }
             ],
             "user" : {
             "domain" : {
               "id" : "default",
               "name" : "Default"
              },
              "id" : "a2bee439945f4f988b4f376aaad46562",
              "name" : "admin",
              "password_expires_at" : null
              }
             }
            }

-------------
API versions
-------------

*******************************************
Lists information about all NFV VIM links
*******************************************

.. rest_method:: GET /

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

::

            {
               "name": "nfv-vim",
               "links": [
                  {
                    "href": "http://192.168.204.2:4545/api/",
                    "rel": "api"
                  }
               ],
               "description": "NFV - Virtual Infrastructure Manager"
            }


**************************************************
Lists information about all NFV VIM API versions
**************************************************

.. rest_method:: GET /api

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

::

   {
     "versions": [
       {
         "status": "stable",
         "id": "v1",
         "links": [
           {
             "href": "http://192.168.204.2:4545/api/",
             "rel": "self"
           },
           {
             "href": "http://192.168.204.2:4545/api/orchestration/",
             "rel": "orchestration"
           }
         ]
       }
     ]
   }

This operation does not accept a request body.

*************************************************************
Lists information about all NFV VIM API orchestration links
*************************************************************

.. rest_method:: GET /api/orchestration

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

::

   {
     "id": "orchestration",
     "links": [
       {
         "href": "http://192.168.204.2:4545/orchestration/",
         "rel": "self"
       },
       {
         "href": "http://192.168.204.2:4545/orchestration/sw-upgrade/",
         "rel": "sw-upgrade"
       },
       {
         "href": "http://192.168.204.2:4545/orchestration/fw-update/",
         "rel": "fw-update"
       },
       {
         "href": "http://192.168.204.2:4545/orchestration/system-config-update/",
         "rel": "system-config-update"
       },
       {
         "href": "http://192.168.204.2:4545/orchestration/current-strategy/",
         "rel": "current-strategy"
       }
     ]
   }

This operation does not accept a request body.

************************************************************************
Lists information about all NFV VIM API orchestration sw-upgrade links
************************************************************************

.. rest_method:: GET /api/orchestration/sw-upgrade

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

::

           {
              "id": "sw-upgrade",
              "links": [
                {
                  "href": "http://192.168.204.2:4545/orchestration/sw-upgrade/",
                  "rel": "self"
                },
                {
                  "href": "http://192.168.204.2:4545/orchestration/sw-upgrade/strategy/",
                  "rel": "strategy"
                }
              ]
           }


**********************************************************************
Lists information about all NFV VIM API orchestration fw-update links
**********************************************************************

.. rest_method:: GET /api/orchestration/fw-update

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

::

   {
     "id": "fw-update",
     "links": [
       {
         "href": "http://192.168.204.2:4545/orchestration/fw-update/",
         "rel": "self"
       },
       {
         "href": "http://192.168.204.2:4545/orchestration/fw-update/strategy/",
         "rel": "strategy"
       }
     ]
   }

This operation does not accept a request body.

*********************************************************************************
Lists information about all NFV VIM API orchestration system-config-update links
*********************************************************************************

.. rest_method:: GET /api/orchestration/system-config-update

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

::

   {
     "id": "system-config-update",
     "links": [
       {
         "href": "http://192.168.204.2:4545/orchestration/system-config-update/",
         "rel": "self"
       },
       {
         "href": "http://192.168.204.2:4545/orchestration/system-config-update/strategy/",
         "rel": "strategy"
       }
     ]
   }

This operation does not accept a request body.

*********************************************************************************
Lists information about all NFV VIM API orchestration current-strategy links
*********************************************************************************

.. rest_method:: GET /api/orchestration/current-strategy

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

::

   {
     "id": "current-strategy",
     "links": [
       {
         "href": "http://192.168.204.2:4545/orchestration/current-strategy/",
         "rel": "self"
       },
       {
         "href": "http://192.168.204.2:4545/orchestration/current-strategy/strategy/",
         "rel": "strategy"
       }
     ]
   }

This operation does not accept a request body.

-------------------------
Software Deploy Strategy
-------------------------

Software deploy orchestration is done with sw-deploy orchestration strategy, or
plan, automated software deployment procedure contains a number of
parameters for customizing the particular behavior of the software deploy
orchestration.

******************************************************************
Shows detailed information about the current sw-deploy strategy
******************************************************************

.. rest_method:: GET /api/orchestration/sw-upgrade/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response parameters**

The details of the strategy can be checked using below response parameter.

* state - 'building or applying or aborting' or 'ready-to-apply or 'applied' 
  or 'aborted' or 'build-failed or apply-failed or abort-failed'.
* result - 'success' or 'failed' or 'aborted'.
* reason and response - It's empty "" on success and on failure it's updated 
  with details of error.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the 
   reason for failure,if any."

**Note**

* Phase - This refers to 'create or apply or abort' phase of strategy
* Stage - This points to various stages at each phase. 
  Example; 'sw-upgrade start deploy', 'sw-upgrade deploy host'
* Step - This refers to different steps executed in each stage. 
  Example; In 'sw-upgrade deploy host' stage, there are different steps like lock-hosts, 
  upgrade-hosts, system-stabilize, unlock-hosts.

When using this API to monitor the progress or status of a create, apply or abort
operation, wait for the 'completion-percentage' parameter to reach 100%.
The 'completion-percentage' is 100% only in success case.
Then, use the 'result' parameter to determine whether it indicates 
'success' or 'failure'. In the failure scenario, the 'reason' and 'response' 
parameters provide more detailed information related to the failure.


**Response body example**

::

            {
               "strategy": {
               "controller-apply-type": "serial",
               "current-phase-completion-percentage": 100,
               "uuid": "ac9b953a-caf1-4abe-8d53-498b598e6731",
               "name": "sw-upgrade",
               "worker-apply-type": "serial",
               "max-parallel-worker-hosts": 2,
               "current-phase": "build",
               "apply-phase": {
               "start-date-time": "",
               "end-date-time": "",
               "phase-name": "apply",
               "completion-percentage": 100,
               "state": "applying",
               "total-stages": 3,
               "stop-at-stage": 0,
               "result": "initial",
               "timeout": 0,
               "reason": "",
               "response": "",
               "inprogress": false,
               "stages": [
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "stage-id": 0,
                 "stage-name": "sw-upgrade-query",
                 "reason": "",
                 "current-step": 0,
                 "steps": [
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "result": "initial",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 3600,
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "start-upgrade",
                 "result": "initial",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 120,
                 "step-id": 0,
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "reason": ""
               }]
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "stage-id": 1,
                 "stage-name": sw-upgrade-worker-hosts,
                 "reason": "",
                 "current-step": 6,
                 "steps": [
                 {
                    "start-date-time": "",
                    "end-date-time": "",
                    "timeout": 60,
                    "step-id": 1,
                    "step-name": "query-alarms",
                    "result": "initial",
                    "reason": ""
                 },
                 {
                    "start-date-time": "",
                    "end-date-time": "",
                    "timeout": 900,
                    "entity-type": "hosts",
                    "step-id": 2,
                    "entity-uuids": [
                       "77f00eea-a346-46f1-bf81-837088616b13"
                    ],
                    "step-name": "lock-hosts",
                    "result": "initial",
                    "entity-names": [
                      "controller-0"
                     ],
                    "reason": ""
                 },
                 {
                    "start-date-time": "",
                    "end-date-time": "",
                    "timeout": 3600,
                    "entity-type": "hosts",
                    "step-id": 3,
                    "step-name": "upgrade-hosts",
                    "result": "initial",
                    "entity-names": [
                      "controller-0"
                    ],
                    "reason": ""
                 },
                 {
                    "start-date-time": "",
                    "end-date-time": "",
                    "timeout": 15,
                    "step-id": 4,
                    "step-name": "system-stabilize",
                    "result": "initial",
                    "reason": ""
                 },
                 {
                    "start-date-time": "",
                    "end-date-time": "",
                    "timeout": 1800,
                    "entity-type": "hosts",
                    "step-id": 5,
                    "entity-uuids": [
                       "77f00eea-a346-46f1-bf81-837088616b13"
                    ],
                    "step-name": "unlock-hosts",
                    "result": "initial",
                    "entity-names": [
                       "controller-0"
                    ],
                    "reason": ""
                 },
                 {
                    "start-date-time": "",
                    "end-date-time": "",
                    "timeout": 2400,
                    "step-id": 6,
                    "step-name": "wait-alarms-clear",
                    "result": "initial",
                    "reason": ""
                 }
                 ],
                   "result": "initial",
                   "timeout": 10861,
                   "total-steps": 5,
                   "inprogress": false,
                   "stage-name": "sw-upgrade-controllers"
                },
                {
                   "start-date-time": "",
                   "end-date-time": "",
                   "stage-id": 1,
                   "reason": "",
                   "current-step": 0,
                   "steps": [
                   {
                     "start-date-time": "",
                     "end-date-time": "",
                     "timeout": 60,
                     "step-id": 1,
                     "step-name": "query-alarms",
                     "result": "initial",
                     "reason": ""
                   },
                   {
                     "start-date-time": "",
                     "end-date-time": "",
                     "timeout": 900,
                     "entity-type": "hosts",
                     "step-id": 2,
                     "entity-uuids": [
                   "2acdfcdc-c29c-46f1-846d-23838ff608cb"],
                 "step-name": "lock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-1"],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 3600,
                 "entity-type": "hosts",
                 "step-id": 2,
                 "entity-uuids": [
                   "2acdfcdc-c29c-46f1-846d-23838ff608cb"],
                 "step-name": "upgrade-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-1"],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 15,
                 "step-id": 4,
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 5,
                 "entity-uuids": [
                   "2acdfcdc-c29c-46f1-846d-23838ff608cb"],
                 "step-name": "unlock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-1"],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 2400,
                 "step-id": 6,
                 "step-name": "wait-alarms-clear",
                 "result": "initial",
                 "reason": ""
               }
             ],
               "result": "initial",
               "timeout": 3721,
               "total-steps": 5,
               "inprogress": false,
               "stage-name": "sw-upgrade-worker-hosts"
             },
             {
               "start-date-time": "",
               "end-date-time": "",
               "stage-id": 2,
               "reason": "",
               "current-step": 0,
               "steps": [
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "step-id": 1,
                 "step-name": "query-alarms",
                 "result": "initial",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 2,
                 "entity-uuids": [
                   "fe3ba4e3-e84d-467f-b633-e23df2f86e90"],
                 "step-name": "lock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "storage-0"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 3600,
                 "entity-type": "hosts",
                 "step-id": 3,
                 "step-name": "upgrade-hosts",
                 "result": "initial",
                 "entity-names": [
                   "storage-0"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 15,
                 "step-id": 4,
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 5,
                 "entity-uuids": [
                   "fe3ba4e3-e84d-467f-b633-e23df2f86e90"],
                 "step-name": "upgrade-hosts",
                 "result": "initial",
                 "entity-names": [
                   "storage-0"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "step-id": 6,
                 "step-name": "wait-data-sync",
                 "result": "initial",
                 "reason": ""
               }]
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "stage-id": 4,
                 "stage-name": sw-upgrade-worker-hosts,
                 "reason": "",
                 "current-step": 6,
                 "steps": [
                 {
                    "start-date-time": "",
                    "end-date-time": "",
                    "timeout": 60,
                    "step-id": 1,
                    "step-name": "query-alarms",
                    "result": "initial",
                    "reason": ""
                 },
                 {
                    "start-date-time": "",
                    "end-date-time": "",
                    "timeout": 900,
                    "entity-type": "hosts",
                    "step-id": 2,
                    "entity-uuids": [
                   "fe3ba4e3-e84d-467f-b633-e23df2f86e90"],
                 "step-name": "unlock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-0"],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 3600,
                 "entity-type": "hosts",
                 "step-id": 3,
                 "step-name": "upgrade-hosts",
                 "result": "initial",
                 "entity-names": [
                   "storage-1"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 15,
                 "step-id": 4,
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "reason": ""
               }
             ],
               "result": "initial",
               "timeout": 3721,
               "total-steps": 5,
               "inprogress": false,
               "stage-name": "sw-upgrade-worker-hosts"
             }
             ],
               "current-stage": 0
             },
               "storage-apply-type": "serial",
               "state": "ready-to-apply",
               "default-instance-action": "migrate",
               "alarm-restrictions": "relaxed",
               "abort-phase": {
               "start-date-time": "",
               "end-date-time": "",
               "phase-name": "abort",
               "completion-percentage": 100,
               "total-stages": 0,
               "stop-at-stage": 0,
               "result": "initial",
               "timeout": 0,
               "reason": "",
               "inprogress": false,
               "stages": [],
               "current-stage": 0
               },
               "build-phase": {
               "start-date-time": "2017-01-10 15:23:12",
               "end-date-time": "2017-01-10 15:23:12",
               "phase-name": "build",
               "completion-percentage": 100,
               "total-stages": 1,
               "stop-at-stage": 1,
               "result": "success",
               "timeout": 122,
               "reason": "",
               "inprogress": false,
               "stages": [
               {
               "start-date-time": "2017-01-10 15:23:12",
               "end-date-time": "2017-01-10 15:23:12",
               "stage-id": 0,
               "reason": "",
               "current-step": 2,
               "steps": [
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "step-id": 1,
                 "step-name": "query-alarms",
                 "result": "initial",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 2,
                 "entity-uuids": [
                   "77f00eea-a346-46f1-bf81-837088616b13"
                 ],
                 "step-name": "lock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-0"
                 ],
                 "reason": ""
               }
             ],
             "result": "success",
             "timeout": 121,
             "total-steps": 2,
             "inprogress": false,
             "stage-name": "sw-upgrade-query"
             }
             ],
             "current-stage": 1
             },
             "swift-apply-type": "ignore"
             }
            }


*******************************
Creates a sw-deploy strategy
*******************************

.. rest_method:: POST /api/orchestration/sw-upgrade/strategy

**Request**

**Request parameters**

.. csv-table::
            :header: "Parameter", "Style", "Type", "Description"
            :widths: 20, 20, 20, 60

            "storage-apply-type", "plain", "xsd:string", "The apply type for storage hosts:
            ``serial``, ``parallel`` or ``ignore``."
            "worker-apply-type", "plain", "xsd:string", "The apply type for worker hosts: ``serial`` ,
            ``parallel`` or ``ignore``."
            "max-parallel-worker-hosts (Optional)", "plain", "xsd:integer", "The maximum number of
            worker hosts to upgrade in parallel; only applicable if ``worker-apply-type = parallel``.
            Default value is ``2``."
            "alarm-restrictions (Optional)", "plain", "xsd:string", "The strictness of alarm checks:
            ``strict`` or ``relaxed`` (recommended option)."
            "release", "plain", "xsd:string", "The release identification name."
            "rollback", "plain", "xsd:bool", "The flag that indicates this is a rollback action."
            "delete", "plain", "xsd:bool", "The flag that indicates that deployment will be marked complete."

**Request body example**

::

          {
             "controller-apply-type": "serial/ignore",
             "default-instance-action": "stop-start/migrate",
             "release": "stx-10.0.1",
             "rollback": false,
             "delete": true,
             "storage-apply-type": "serial/ignore",
             "worker-apply-type": "serial/parallel/ignore",
             "alarm-restrictions": "strict/relaxed"
          }

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Response parameters**

The "sw-deploy create strategy" request starts the creation process of the strategy,
and returns a response to indicate the status of the creation process. 
E.g. typically after initially starting the create.

* state ='building'.
* current-phase ='build'

Use the sw-deploy get strategy request to monitor the progress and status of the create.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the 
   reason for failure,if any."

**Response body example**

::

            {
                "strategy": {
                  "controller-apply-type": "serial",
                  "current-phase-completion-percentage": 0,
                  "uuid": "ac9b953a-caf1-4abe-8d53-498b598e6731",
                  "release-id": "stx-10.0.1",
                  "worker-apply-type": "serial",
                  "storage-apply-type": "serial",
                  "max-parallel-worker-hosts": 2,
                  "current-phase": "build",
                  "apply-phase": {
                  "start-date-time": "",
                  "end-date-time": "",
                  "phase-name": "apply",
                  "completion-percentage": 100,
                  "total-stages": 0,
                  "stop-at-stage": 0,
                  "result": "initial",
                  "timeout": 0,
                  "reason": "",
                  "inprogress": true,
                  "stages": [],
                  "current-stage": 0,
                  },
                  "storage-apply-type": "serial",
                  "state": "building",
                  "default-instance-action": "migrate",
                  "alarm-restrictions": "relaxed",
                  "abort-phase": {
                  "start-date-time": "",
                  "end-date-time": "",
                  "phase-name": "abort",
                  "completion-percentage": 100,
                  "total-stages": 0,
                  "stop-at-stage": 0,
                  "result": "initial",
                  "timeout": 0,
                  "reason": "",
                  "inprogress": false,
                  "stages": [],
                  "current-stage": 0
                  },
                  "build-phase": {
                  "start-date-time": "",
                  "end-date-time": "",
                  "phase-name": "build",
                  "completion-percentage": 0,
                  "total-stages": 1,
                  "stop-at-stage": 1,
                  "result": "inprogress",
                  "timeout": 182 seconds,
                  "reason": "",
                  "inprogress": true,
                  "stages": [
                  {
                  "start-date-time": "",
                  "end-date-time": "",
                  "stage-id": 0,
                  "stage-name": "sw-upgrade-query",
                  "reason": "",
                  "current-step": 3,
                  "steps": [
                  {
                  "start-date-time": "",
                  "end-date-time": "",
                  "timeout": 60,
                  "step-id": 1,
                  "step-name": "query-alarms",
                  "result": "wait",
                  "reason": ""
                  },
                  {
                  "start-date-time": "",
                  "end-date-time": "",
                  "timeout": 60,
                  "step-id": 2,
                  "step-name": "query-upgrade",
                  "result": "initial",
                  "reason": ""
                  },
                  {
                  "start-date-time": "",
                  "end-date-time": "",
                  "timeout": 60,
                  "step-id": 3,
                  "step-name": "sw-deploy-precheck",
                  "result": "initial",
                  "reason": ""
                  },
                  ]
                  "result": "inprogress",
                  "timeout": 121,
                  "total-steps": 3,
                  "inprogress": true,
                  "stage-name": "sw-upgrade-query"
                  }]
                  }
                  "swift-apply-type": "ignore"
                  }
                }
              }


*****************************************
Deletes the current sw-upgrade strategy
*****************************************

.. rest_method:: DELETE /api/orchestration/sw-upgrade/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

204

**Response body example**

::

           {
           }


*****************************************
Applies or aborts a sw-deploy strategy
*****************************************

.. rest_method:: POST /api/orchestration/sw-upgrade/strategy/actions

**Request**

**Request body parameters**

These parameters are common for both apply and abort strategy.

.. csv-table::
           :header: "Parameter", "Style", "Type", "Description"
           :widths: 20, 20, 20, 60

           "action", "plain", "xsd:string", "The action to take: ``apply-all``, 
           ``apply-stage``,``abort`` or ``abort-stage``."
           "stage-id", "plain", "xsd:string", "The stage-id to apply or abort.
           Only used with ``apply-stage`` or ``abort-stage`` actions."

**Note**

* stage-id - This is used to apply or abort a particular stage in the execution flow.
  Each stage has a number specified. This can be identified from the response 
  parameter 'stage-id' which can be used to apply or abort a specific stage.
* apply-all or abort-all - This is recommended option, as it takes care of applying 
  or aborting all the required stages."

**Request body example**

::

           {
             "action": "apply-all"
           }

**Response**

**Normal response codes**

202

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Response parameters**

The "sw-deploy" strategy "apply" or "abort" request starts the apply or abort process,
and returns a response to indicate the current status of the apply or abort process. 
E.g. typically after initially starting the create.

* state = 'applying' or 'aborting'.
* current-phase ='apply' or 'abort'

Use the sw-deploy get strategy request to monitor the progress and status of the apply.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the 
   reason for failure,if any."

**Response body example**

::

            {
              "strategy": {
              "controller-apply-type": "serial",
              "current-phase-completion-percentage": 0,
              "uuid": "ac9b953a-caf1-4abe-8d53-498b598e6731",
              "name": "sw-upgrade",
              "worker-apply-type": "serial",
              "max-parallel-worker-hosts": 2,
              "current-phase": "apply",
              "apply-phase": {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "phase-name": "apply",
              "completion-percentage": 0,
              "total-stages": 3,
              "stop-at-stage": 3,
              "result": "inprogress",
              "timeout": 18304,
              "reason": "",
              "inprogress": true,
              "stages": [
              {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "stage-id": 0,
              "reason": "",
              "current-step": 0,
              "steps": [
              {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "timeout": 60,
              "entity-type": "",
              "step-id": 0,
              "entity-uuids": [],
              "step-name": "query-alarms",
              "result": "wait",
              "entity-names": [],
              "reason": ""
              },
              {
              "start-date-time": "",
              "end-date-time": "",
              "timeout": 900,
              "entity-type": "hosts",
              "step-id": 1,
              "entity-uuids": [
                "77f00eea-a346-46f1-bf81-837088616b13"
              ],
              "step-name": "lock-hosts",
              "result": "initial",
              "entity-names": [
              "controller-0"
              ],
              "reason": ""
              },
              {
              "start-date-time": "",
              "end-date-time": "",
              "timeout": 1800,
              "entity-type": "hosts",
              "step-id": 2,
              "entity-uuids": [
                "77f00eea-a346-46f1-bf81-837088616b13"
              ],
              "step-name": "upgrade-hosts",
              "result": "initial",
              "entity-names": [
                "controller-0"],
              "reason": ""
              },
              {
              "start-date-time": "",
              "end-date-time": "",
              "timeout": 900,
              "entity-type": "hosts",
              "step-id": 3,
              "entity-uuids": [
                 "77f00eea-a346-46f1-bf81-837088616b13"
               ],
               "step-name": "unlock-hosts",
               "result": "initial",
               "entity-names": [
                 "controller-0"],
                 "reason": ""
               },
               {
               "start-date-time": "",
               "end-date-time": "",
               "timeout": 7200,
               "entity-type": "",
               "step-id": 4,
               "entity-uuids": [],
               "step-name": "wait-data-sync",
               "result": "initial",
               "entity-names": [],
               "reason": ""
               }
             ],
             "result": "inprogress",
             "timeout": 10861,
             "total-steps": 5,
             "inprogress": true,
             "stage-name": "sw-upgrade-controllers"
            },
            {
             "start-date-time": "",
             "end-date-time": "",
             "stage-id": 1,
             "reason": "",
             "current-step": 0,
             "steps": [
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "result": "initial",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 1,
                 "entity-uuids": [
                   "2acdfcdc-c29c-46f1-846d-23838ff608cb"
                 ],
                 "step-name": "lock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-1"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 3600,
                 "entity-type": "hosts",
                 "step-id": 2,
                 "entity-uuids": [
                   "2acdfcdc-c29c-46f1-846d-23838ff608cb"
                 ],
                 "step-name": "upgrade-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-1"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 15,
                 "step-id": 3,
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 4,
                 "entity-uuids": [
                   "2acdfcdc-c29c-46f1-846d-23838ff608cb"
                 ],
                 "step-name": "unlock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-1"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 15,
                 "step-id": 5,
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "reason": ""
               }
             ],
             "result": "initial",
             "timeout": 3721,
             "total-steps": 5,
             "inprogress": false,
             "stage-name": "sw-upgrade-worker-hosts"
            },
            {
             "start-date-time": "",
             "end-date-time": "",
             "stage-id": 2,
             "reason": "",
             "current-step": 0,
             "steps": [
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "result": "initial",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 1,
                 "entity-uuids": [
                   "fe3ba4e3-e84d-467f-b633-e23df2f86e90"
                 ],
                 "step-name": "lock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-0"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 3600,
                 "entity-type": "hosts",
                 "step-id": 2,
                 "entity-uuids": [
                   "fe3ba4e3-e84d-467f-b633-e23df2f86e90"
                 ],
                 "step-name": "upgrade-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-0"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 15,
                 "step-id": 3,
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 4,
                 "entity-uuids": [
                   "fe3ba4e3-e84d-467f-b633-e23df2f86e90"
                 ],
                 "step-name": "unlock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-0"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "step-id": 5,
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "reason": ""
               }
             ],
             "result": "initial",
             "timeout": 3721,
             "total-steps": 5,
             "inprogress": false,
             "stage-name": "sw-upgrade-worker-hosts"
             }
             ],
             "current-stage": 0
             },
             "storage-apply-type": "serial",
             "state": "applying",
             "default-instance-action": "migrate",
             "alarm-restrictions": "relaxed",
             "abort-phase": {
             "start-date-time": "",
             "end-date-time": "",
             "phase-name": "abort",
             "completion-percentage": 100,
             "total-stages": 0,
             "stop-at-stage": 0,
             "result": "initial",
             "timeout": 0,
             "reason": "",
             "inprogress": false,
             "stages": [],
             "current-stage": 0
             },
             "build-phase": {
             "start-date-time": "2017-01-10 15:23:12",
             "end-date-time": "2017-01-10 15:23:12",
             "phase-name": "build",
             "completion-percentage": 100,
             "total-stages": 1,
             "stop-at-stage": 1,
             "result": "success",
             "timeout": 122,
             "reason": "",
             "inprogress": false,
             "stages": [
             {
             "start-date-time": "2017-01-10 15:23:12",
             "end-date-time": "2017-01-10 15:23:12",
             "stage-id": 0,
             "reason": "",
             "current-step": 3,
             "steps": [
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "step-id": 1,
                 "step-name": "query-alarms",
                 "result": "success",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "step-id": 2,
                 "step-name": "query-upgrade",
                 "result": "success",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "step-id": 3,
                 "step-name": "sw-deploy-precheck",
                 "result": "success",
                 "reason": ""
               }
             ],
             "result": "success",
             "timeout": 121,
             "total-steps": 2,
             "inprogress": false,
             "stage-name": "sw-upgrade-query"
             }
             ],
             "current-stage": 1
             },
             "swift-apply-type": "ignore"
             }
            }

----------------------------
Kubernetes Upgrade Strategy
----------------------------

Kubernetes upgrade orchestration is performed with a kube upgrade orchestration
strategy, or plan, for the automated upgrade of kubernetes components to the 
target version. A kube-upgrade strategy is capable of upgrading multiple versions
at once in simplex system configuration. In other system configurations,
kube-upgrade strategy can upgrade only single version at a time.
Kubernetes upgrade contains a number of parameters for customizing the particular 
behavior of the kubernetes upgrade orchestration.

**********************************************************
Shows detailed information about the kubernetes strategy
**********************************************************

.. rest_method:: GET /api/orchestration/kube-upgrade/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response parameters**

The details of the strategy can be checked using below response parameter.

* state - 'building or applying or aborting' or 'ready-to-apply or applied 
  or aborted' or 'build-failed or apply-failed or abort-failed'.
* result - 'success' or 'failed' or 'aborted'.
* reason and response - It's empty "" on success and on failure it's updated 
  with details of error.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."


**Response body example**
::

   {
       "strategy": {
       "controller-apply-type": "ignore",
       "swift-apply-type": "ignore",
       "storage-apply-type": "ignore",
       "worker-apply-type": "serial",
       "state": "ready-to-apply",
       "default-instance-action": "stop-start",
       "max-parallel-worker-hosts": 2,
       "alarm-restrictions": "strict",
       "current-phase-completion-percentage": 100,
       "uuid": "5dd16d94-dfc5-4029-bfcb-d815e7c2dc3d",
       "name": "kube-upgrade",
       "current-phase": "build",
       "build-phase": {
         "phase-name": "build",
         "current-stage": 1,
         "total-stages": 1,
         "completion-percentage": 100,
         "start-date-time": "2025-03-26 13:31:02",
         "end-date-time": "2025-03-26 13:31:02"
         "stop-at-stage": 1,
         "result": "success",
         "timeout": 982,
         "reason": "",
         "inprogress": false,
         "stages": [
          {
             "start-date-time": "",
             "end-date-time": "",
             "stage-id": 0,
             "stage-name": "kube-upgrade-query",
             "reason": "",
             "current-step": 0,
             "steps": [
          {
             "start-date-time": "",
             "end-date-time": "",
             "timeout": 60,
             "step-id": 0,
             "step-name": "query-kube-versions",
             "result": "initial",
             "reason": ""
         },
         {
             "start-date-time": "",
             "end-date-time": "",
             "timeout": 60,
             "step-id": 0,
             "entity-uuids": [],
             "step-name": "query-kube-upgrade",
             "result": "initial",
             "reason": ""
         },
         {
             "start-date-time": "",
             "end-date-time": "",
             "timeout": 200,
             "step-id": 0,
             "step-name": "query-kube-host-upgrade",
             result": "initial",
             "reason": ""
         }]
      }
   }

This operation does not accept a request body.

********************************
Creates a kube-upgrade strategy
********************************

.. rest_method:: POST /api/orchestration/kube-upgrade/strategy

**Request**

**Request parameters**

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "controller-apply-type", "plain", "xsd:string", "The apply type for controller hosts: ``ignore``."
   "storage-apply-type", "plain", "xsd:string", "The apply type for storage hosts: ``ignore``."
   "worker-apply-type", "plain", "xsd:string", "The apply type for worker hosts: ``serial``, 
   ``parallel`` or ``ignore``."
   "max-parallel-worker-hosts (Optional)", "plain", "xsd:integer", "The maximum number of 
   worker hosts to patch in parallel; only applicable if ``worker-apply-type = parallel``. 
   Default value is ``2``."
   "default-instance-action", "plain", "xsd:string", "The default instance action: 
   ``stop-start`` or ``migrate``."
   "alarm-restrictions (Optional)", "plain", "xsd:string", "The strictness of alarm checks: 
   ``strict`` or ``relaxed`` (recommended option)"
   "to-version (mandatory)", "plain", "xsd:string", "The kubernetes version to upgrade"

**Request body example**

::

   {
     "controller-apply-type": "serial",
     "storage-apply-type": "serial",
     "worker-apply-type": "serial",
     "default-instance-action": "stop-start",
     "alarm-restrictions": "relaxed",
     "to-version": "v1.31.5"
   }

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Response parameters**

The kubernetes create strategy request starts the creation process of the strategy,
and returns a response to indicate the status of the creation process. 
E.g. typically after initially starting the create.

* state ='building'.
* current-phase ='build'

Use the kubernetes get strategy request to monitor the progress and status of the create.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."

**Response body example**

::

   {
       "strategy": {
       "controller-apply-type": "ignore",
       "swift-apply-type": "ignore",
       "storage-apply-type": "ignore",
       "worker-apply-type": "serial",
       "state": "ready-to-apply",
       "default-instance-action": "stop-start",
       "max-parallel-worker-hosts": 2,
       "alarm-restrictions": "strict",
       "current-phase-completion-percentage": 100,
       "uuid": "5dd16d94-dfc5-4029-bfcb-d815e7c2dc3d",
       "name": "kube-upgrade",
       "current-phase": "build",
       "build-phase": {
         "phase-name": "build",
         "current-stage": 1,
         "total-stages": 1,
         "completion-percentage": 100,
         "start-date-time": "2025-03-26 13:31:02",
         "end-date-time": "2025-03-26 13:31:02"
         "stop-at-stage": 1,
         "result": "success",
         "timeout": 982,
         "reason": "",
         "inprogress": false,
         "stages": [
          {
             "start-date-time": "",
             "end-date-time": "",
             "stage-id": 0,
             "reason": "",
             "current-step": 0,
             "steps": [
          {
             "start-date-time": "",
             "end-date-time": "",
             "timeout": 60,
             "step-id": 0,
             "step-name": "query-kube-versions",
             "result": "initial",
             "reason": ""
         },
         {
             "start-date-time": "",
             "end-date-time": "",
             "timeout": 60,
             "step-id": 0,
             "entity-uuids": [],
             "step-name": "query-kube-upgrade",
             "result": "initial",
             "reason": ""
         }]
       }
       "apply-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "apply",
         "completion-percentage": 100,
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [],
         "current-stage": 0
       },
       "abort-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "abort",
         "completion-percentage": 100,
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress":false,
         "stages": [],
         "current-stage": 0
      }
   }


*******************************************
Deletes the current kube-upgrade strategy
*******************************************

.. rest_method:: DELETE /api/orchestration/kube-upgrade/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

204

**Response body example**

::

   {
   }

****************************************
Applies or aborts kube-upgrade strategy
****************************************

.. rest_method:: POST /api/orchestration/kube-upgrade/strategy/actions

**Request**

**Request parameters**

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "action", "plain", "xsd:string", "The action to take: ``apply-all``, ``apply-stage``, 
   ``abort``or ``abort-stage``."
   "stage-id (Optional)", "plain", "xsd:string", "The stage-id to apply or abort. 
   Only used with ``apply-stage`` or ``abort-stage`` actions."

**Note**

* stage-id - This is used to apply or abort a particular stage in the execution flow.
  Each stage has a number specified. This can be identified from the response parameter 
  'stage-id' which can be used to apply or abort a specific stage.
* apply-all or abort-all - This is recommended option, as it takes care of applying 
  or aborting all the required stages."

**Request body example**

::

   {
     "action": "apply-all"
   }

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response parameters**

The kubernetes strategy apply or abort request starts the apply or abort process,
and returns a response to indicate the current status of the apply or abort process. 
E.g. typically after initially starting the create.

* state = 'applying' or 'aborting'.
* current-phase ='apply' or 'abort'

Use the kubernetes get strategy request to monitor the progress and status of Apply strategy.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."

**Response body example**

::

   {
       "strategy": {
       "controller-apply-type": "ignore",
       "swift-apply-type": "ignore",
       "storage-apply-type": "ignore",
       "worker-apply-type": "serial",
       "state": "ready-to-apply",
       "default-instance-action": "stop-start",
       "max-parallel-worker-hosts": 2,
       "alarm-restrictions": "strict",
       "current-phase-completion-percentage": 100,
       "uuid": "5dd16d94-dfc5-4029-bfcb-d815e7c2dc3d",
       "name": "kube-upgrade",
       "current-phase": "build",
       "build-phase": {
         "phase-name": "build",
         "current-stage": 1,
         "total-stages": 1,
         "completion-percentage": 100,
         "start-date-time": "2025-03-26 13:31:02",
         "end-date-time": "2025-03-26 13:31:02"
         "stop-at-stage": 1,
         "result": "success",
         "timeout": 982,
         "reason": "",
         "inprogress": false,
         "stages": [
          {
             "start-date-time": "",
             "end-date-time": "",
             "stage-id": 0,
             "stage-name": "kube-upgrade-query",
             "reason": "",
             "current-step": 0,
             "steps": [
          {
             "start-date-time": "",
             "end-date-time": "",
             "timeout": 60,
             "step-id": 0,
             "step-name": "query-kube-versions",
             "result": "initial",
             "reason": ""
         },
         {
             "start-date-time": "",
             "end-date-time": "",
             "timeout": 60,
             "step-id": 0,
             "entity-uuids": [],
             "step-name": "query-kube-upgrade",
             "result": "initial",
             "reason": ""
         }]
       }
       "apply-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "apply",
         "completion-percentage": 100,
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [],
         "current-stage": 0
       },
       "abort-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "abort",
         "completion-percentage": 100,
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress":false,
         "stages": [],
         "current-stage": 0
      }
   }


------------------------
Firmware Update Strategy
------------------------

Firmware update orchestration is done with a firmware update orchestration
strategy, or plan, for the automated update procedure which contains a number
of parameters for customizing the particular behavior of the firmware update
orchestration.

***************************************************************
Shows detailed information about the current fw-update strategy
***************************************************************

.. rest_method:: GET /api/orchestration/fw-update/strategy

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

::

   {
     "strategy": {
       "controller-apply-type": "ignore",
       "swift-apply-type": "ignore",
       "storage-apply-type": "ignore",
       "worker-apply-type": "serial",
       "state": "ready-to-apply",
       "default-instance-action": "stop-start",
       "max-parallel-worker-hosts": 2,
       "alarm-restrictions": "strict",
       "current-phase-completion-percentage": 100,
       "uuid": "5dd16d94-dfc5-4029-bfcb-d815e7c2dc3d",
       "name": "fw-update",
       "current-phase": "build",
       "build-phase": {
         "phase-name": "build",
         "current-stage": 1,
         "total-stages": 1,
         "completion-percentage": 100,
         "start-date-time": "2020-05-05 21:07:18",
         "end-date-time": "2020-05-05 21:07:19",
         "stop-at-stage": 1,
         "result": "success",
         "timeout": 182,
         "reason": "",
         "inprogress": false,
         "stages": [
           {
             "stage-id": 0,
             "total-steps": 3,
             "stage-name": "fw-update-hosts-query",
             "result": "success",
             "timeout": 181,
             "inprogress": false,
             "start-date-time": "2020-05-05 21:07:18",
             "end-date-time": "2020-05-05 21:07:19",
             "reason": "",
             "current-step" : 3,
             "steps":[
               {
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "2020-05-05 21:07:18",
                 "end-date-time": "2020-05-05 21:07:19",
                 "timeout": 60,
                 "result": "success",
                 "reason": ""
               },
               {
                 "step-id": 1,
                 "step-name": "query-host-devices",
                 "entity-type": "",
                 "entity-names": ["compute-1"],
                 "entity-uuids": ["ecff0928-9655-46ed-9ac0-433dfa21c7e2"],
                 "start-date-time": "2020-05-05 21:07:19",
                 "end-date-time": "2020-05-05 21:07:19",
                 "timeout": 60,
                 "result": "success",
                 "reason": ""
               },
               {
                 "step-id": 2,
                 "step-name": "query-host-devices",
                 "entity-type": "",
                 "entity-names": ["compute-0"],
                 "entity-uuids": ["fa62c159-7b2c-47f5-bbda-126bc5e7de21"],
                 "start-date-time": "2020-05-05 21:07:19",
                 "end-date-time": "2020-05-05 21:07:19",
                 "timeout": 60,
                 "result": "success",
                 "reason": ""
               }
             ]
           }
         ]
       },
       "apply-phase": {
         "phase-name": "apply",
         "current-stage": 0,
         "completion-percentage": 100,
         "total-stages": 2,
         "stop-at-stage": 0,
         "start-date-time": "",
         "end-date-time": "",
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [
           {
             "stage-id": 0,
             "stage-name": "fw-update-worker-hosts",
             "start-date-time": "",
             "end-date-time": "",
             "current-step": 0,
             "result": "initial",
             "timeout": 6436,
             "inprogress": false,
             "reason": "",
             "total-steps": 6,
             "steps": [
               {
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "step-id": 1,
                 "entity-type": "hosts",
                 "step-name": "fw-update-hosts",
                 "entity-names": ["compute-1"],
                 "entity-uuids": ["ecff0928-9655-46ed-9ac0-433dfa21c7e2"],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 3600,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "step-id": 2,
                 "entity-type": "hosts",
                 "step-name": "lock-hosts",
                 "entity-names": ["compute-1"],
                 "entity-uuids": ["ecff0928-9655-46ed-9ac0-433dfa21c7e2"],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "step-id": 3,
                 "entity-type": "",
                 "step-name": "system-stabilize",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 15,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "step-id": 4,
                 "entity-type": "hosts",
                 "step-name": "unlock-hosts",
                 "entity-names": ["compute-1"],
                 "entity-uuids": ["ecff0928-9655-46ed-9ac0-433dfa21c7e2"],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "step-id": 5,
                 "entity-type": "",
                 "step-name": "system-stabilize",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "initial",
                 "reason": ""
               }
             ],
           },
           {
             "stage-id": 1,
             "total-steps": 6,
             "stage-name": "fw-update-worker-hosts",
             "inprogress": false,
             "start-date-time": "",
             "end-date-time": "",
             "timeout": 6436,
             "reason": "",
             "result": "initial",
             "current-step": 0,
             "steps":[
               {
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "step-id":1,
                 "step-name": "fw-update-hosts",
                 "entity-type": "hosts",
                 "entity-names": ["compute-0"],
                 "entity-uuids": ["fa62c159-7b2c-47f5-bbda-126bc5e7de21"],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 3600,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "step-id": 2,
                 "step-name": "lock-hosts",
                 "entity-type": "hosts",
                 "entity-names": ["compute-0"],
                 "entity-uuids": ["fa62c159-7b2c-47f5-bbda-126bc5e7de21"],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "step-id": 3,
                 "step-name": "system-stabilize",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 15,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "step-id": 4,
                 "step-name": "unlock-hosts",
                 "entity-type": "hosts",
                 "entity-names": ["compute-0"],
                 "entity-uuids": ["fa62c159-7b2c-47f5-bbda-126bc5e7de21"],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "step-id": 5,
                 "step-name": "system-stabilize",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "initial",
                 "reason": ""
               }
             ],
           }
         ],
       },
       "abort-phase": {
         "phase-name": "abort",
         "total-stages": 0,
         "completion-percentage": 100,
         "start-date-time": "",
         "end-date-time": "",
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [],
         "current-stage": 0
       }
     }
   }

This operation does not accept a request body.

****************************
Creates a fw-update strategy
****************************

.. rest_method:: POST /api/orchestration/fw-update/strategy

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Request parameters**

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "controller-apply-type", "plain", "xsd:string", "The apply type for controller hosts: ``ignore``."
   "storage-apply-type", "plain", "xsd:string", "The apply type for storage hosts: ``ignore``."
   "worker-apply-type", "plain", "xsd:string", "The apply type for worker hosts: ``serial``, 
   ``parallel`` or ``ignore``."
   "max-parallel-worker-hosts (Optional)", "plain", "xsd:integer", 
   "The maximum number of worker hosts to patch in parallel; only applicable if 
   ``worker-apply-type = parallel``. Default value is ``2``."
   "default-instance-action", "plain", "xsd:string", "The default instance action: 
   ``stop-start`` or ``migrate``."
   "alarm-restrictions (Optional)", "plain", "xsd:string", "The strictness of alarm checks: 
   ``strict`` or ``relaxed``."

::

   {
     "controller-apply-type": "ignore",
     "storage-apply-type": "ignore",
     "worker-apply-type": "serial",
     "default-instance-action": "stop-start",
     "alarm-restrictions": "strict",
   }

::

   {
     "strategy": {
       "name": "fw-update",
       "worker-apply-type": "serial",
       "controller-apply-type": "ignore",
       "swift-apply-type": "ignore",
       "storage-apply-type": "ignore",
       "current-phase-completion-percentage": 0,
       "uuid": "447c4267-0ecb-48f4-9237-1d747a3e7cca",
       "default-instance-action": "stop-start",
       "max-parallel-worker-hosts": 2,
       "alarm-restrictions": "strict",
       "state": "building",
       "build-phase": {
         "phase-name": "build",
         "current-stage": 0,
         "start-date-time": "2020-05-06 13:26:11",
         "end-date-time": "",
         "completion-percentage": 0,
         "stop-at-stage": 1,
         "result": "inprogress",
         "timeout": 182,
         "reason": "",
         "inprogress": true,
         "total-stages": 1,
         "stages": [
           {
             "stage-id": 0,
             "stage-name": "fw-update-hosts-query",
             "total-steps": 3,
             "inprogress": true,
             "start-date-time": "2020-05-06 13:26:11",
             "end-date-time": "",
             "reason": "",
             "current-step": 0,
             "result": "inprogress",
             "timeout": 181,
             "steps": [
               {
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "2020-05-06 13:26:11",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "wait",
                 "reason": ""
               },
               {
                 "step-id": 1,
                 "step-name": "query-host-devices",
                 "entity-type": "",
                 "entity-names": ["compute-1"],
                 "entity-uuids": ["ecff0928-9655-46ed-9ac0-433dfa21c7e2"],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "step-id": 2,
                 "step-name": "query-host-devices",
                 "entity-type": "",
                 "entity-names": ["compute-0"],
                 "entity-uuids": ["fa62c159-7b2c-47f5-bbda-126bc5e7de21"],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "initial",
                 "reason": ""
               }
             ],
           }
         ],
       },
       "apply-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "apply",
         "completion-percentage": 100,
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [],
         "current-stage": 0
       },
       "abort-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "abort",
         "completion-percentage": 100,
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress":false,
         "stages": [],
         "current-stage": 0
       }
     }
   }

**************************************
Deletes the current fw-update strategy
**************************************

.. rest_method:: DELETE /api/orchestration/fw-update/strategy

**Normal response codes**

204

::

   {
   }

**************************************
Applies or aborts a fw-update strategy
**************************************

.. rest_method:: POST /api/orchestration/fw-update/strategy/actions

**Normal response codes**

202

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Request parameters**

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "action", "plain", "xsd:string", "The action to take: ``apply-all``, ``apply-stage``, 
   ``abort`` or ``abort-stage``."
   "stage-id (Optional)", "plain", "xsd:string", "The stage-id to apply or abort. 
   Only used with ``apply-stage`` or ``abort-stage`` actions."

**Note**

* stage-id - This is used to apply or abort a particular stage in the execution flow.
  Each stage has a number specified. This can be identified from the response parameter 
  'stage-id' which can be used to apply or abort a specific stage.
* apply-all or abort-all - This is recommended option, as it takes care of applying 
  or aborting all the required stages."

::

   {
     "action": "apply-all"
   }

::

   {
     "strategy":{
       "controller-apply-type": "ignore",
       "swift-apply-type": "ignore",
       "current-phase-completion-percentage": 0,
       "uuid": "447c4267-0ecb-48f4-9237-1d747a3e7cca",
       "name": "fw-update",
       "current-phase": "build",
       "storage-apply-type": "ignore",
       "state":"building",
       "worker-apply-type": "serial",
       "default-instance-action": "stop-start",
       "max-parallel-worker-hosts": 2,
       "alarm-restrictions": "strict",
       "build-phase": {
         "phase-name": "build",
         "current-stage": 0,
         "start-date-time": "2020-05-06 13:26:11",
         "end-date-time": "",
         "completion-percentage": 0,
         "stop-at-stage": 1,
         "result": "inprogress",
         "timeout": 182,
         "reason": "",
         "inprogress": true,
         "total-stages": 1,
         "stages": [
           {
             "stage-id": 0,
             "stage-name": "fw-update-hosts-query",
             "total-steps": 3,
             "inprogress": true,
             "start-date-time": "2020-05-06 13:26:11",
             "end-date-time": "",
             "reason": "",
             "current-step": 0,
             "result": "inprogress",
             "timeout": 181,
             "steps": [
               {
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "2020-05-06 13:26:11",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "wait",
                 "reason": ""
               },
               {
                 "step-id": 1,
                 "step-name": "query-host-devices",
                 "entity-type": "",
                 "entity-names": ["compute-1"],
                 "entity-uuids": ["ecff0928-9655-46ed-9ac0-433dfa21c7e2"],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "step-id": 2,
                 "step-name": "query-host-devices",
                 "entity-type": "",
                 "entity-names": ["compute-0"],
                 "entity-uuids": ["fa62c159-7b2c-47f5-bbda-126bc5e7de21"],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "initial",
                 "reason": ""
               }
             ]
           }
         ]
       },
       "apply-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "apply",
         "completion-percentage": 100,
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [],
         "current-stage": 0
       },
       "abort-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "abort",
         "completion-percentage": 100,
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [],
         "current-stage": 0
       }
     }
   }

------------------------------
System Config Update Strategy
------------------------------

System config update orchestration is done with a system config update
orchestration strategy, or plan, for the automated update procedure which
contains a number of parameters for customizing the particular behavior of the
system config update orchestration.

***************************************************************************
Shows detailed information about the current system-config-update strategy
***************************************************************************

.. rest_method:: GET /api/orchestration/system-config-update/strategy

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

::

   {
     "strategy": {
       "controller-apply-type": "serial",
       "swift-apply-type": "ignore",
       "storage-apply-type": "serial",
       "worker-apply-type": "parallel",
       "state": "ready-to-apply",
       "default-instance-action": "stop-start",
       "max-parallel-worker-hosts": 4,
       "alarm-restrictions": "strict",
       "current-phase-completion-percentage": 100,
       "uuid": "5dd16d94-dfc5-4029-bfcb-d815e7c2dc3d",
       "name": "system-config-update",
       "current-phase": "build",
       "build-phase": {
         "phase-name": "build",
         "current-stage": 1,
         "total-stages": 1,
         "completion-percentage": 100,
         "start-date-time": "",
         "end-date-time": "",
         "stop-at-stage": 1,
         "result": "success",
         "timeout": 182,
         "reason": "",
         "inprogress": false,
         "stages": [
           {
             "stage-id": 0,
             "total-steps": 3,
             "stage-name": "system-config-update-hosts-query",
             "result": "success",
             "timeout": 181,
             "inprogress": false,
             "start-date-time": "",
             "end-date-time": "",
             "reason": "",
             "current-step" : 3,
             "steps":[
               {
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "success",
                 "reason": ""
               },
               {
                 "step-id": 1,
                 "step-name": "query-strategy-required",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "success",
                 "reason": ""
               },
               {
                 "step-id": 2,
                 "step-name": "query-in-sync",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "success",
                 "reason": ""
               }
             ]
           }
         ]
       },
       "apply-phase": {
         "phase-name": "apply",
         "current-stage": 0,
         "completion-percentage": 100,
         "total-stages": 2,
         "stop-at-stage": 0,
         "start-date-time": "",
         "end-date-time": "",
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [
           {
             "stage-id": 0,
             "stage-name": "system-config-update-controllers",
             "start-date-time": "",
             "end-date-time": "",
             "current-step": 0,
             "result": "initial",
             "timeout": 6436,
             "inprogress": false,
             "reason": "",
             "total-steps": 6,
             "steps": [
               {
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 1,
                 "entity-uuids": [
                   "523cbd2d-f7f8-4707-8617-d085386f8711"
                 ],
                 "step-name": "swact-hosts",
                 "result": "initial",
                 "entity-names": [
                   "controller-1"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 2,
                 "entity-uuids": [
                   "523cbd2d-f7f8-4707-8617-d085386f8711"
                 ],
                 "step-name": "lock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "controller-1"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 3,
                 "entity-uuids": [
                   "523cbd2d-f7f8-4707-8617-d085386f8711"
                 ],
                 "step-name": "config-disabled-host",
                 "result": "initial",
                 "entity-names": [
                   "controller-1"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 4,
                 "entity-uuids": [
                   "523cbd2d-f7f8-4707-8617-d085386f8711"
                 ],
                 "step-name": "unlock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "controller-1"
                 ],
                 "reason": ""
               },
               {
                 "step-id": 5,
                 "entity-type": "",
                 "step-name": "system-stabilize",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "initial",
                 "reason": ""
               }
             ],
           },
           {
             "stage-id": 1,
             "total-steps": 6,
             "stage-name": "system-config-update-controllers",
             "inprogress": false,
             "start-date-time": "",
             "end-date-time": "",
             "timeout": 6436,
             "reason": "",
             "result": "initial",
             "current-step": 0,
             "steps":[
               {
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "initial",
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 1,
                 "entity-uuids": [
                   "0f3715c0-fecd-46e0-9cd0-4fbb31810393"
                 ],
                 "step-name": "swact-hosts",
                 "result": "initial",
                 "entity-names": [
                   "controller-0"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 2,
                 "entity-uuids": [
                   "0f3715c0-fecd-46e0-9cd0-4fbb31810393"
                 ],
                 "step-name": "lock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "controller-0"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 3,
                 "entity-uuids": [
                   "0f3715c0-fecd-46e0-9cd0-4fbb31810393"
                 ],
                 "step-name": "config-disabled-host",
                 "result": "initial",
                 "entity-names": [
                   "controller-0"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 4,
                 "entity-uuids": [
                   "0f3715c0-fecd-46e0-9cd0-4fbb31810393"
                 ],
                 "step-name": "unlock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "controller-0"
                 ],
                 "reason": ""
               },
               {
                 "step-id": 5,
                 "entity-type": "",
                 "step-name": "system-stabilize",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "initial",
                 "reason": ""
               }
             ],
           }
         ],
       },
       "abort-phase": {
         "phase-name": "abort",
         "total-stages": 0,
         "completion-percentage": 100,
         "start-date-time": "",
         "end-date-time": "",
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [],
         "current-stage": 0
       }
     }
   }

This operation does not accept a request body.

****************************************
Creates a system-config-update strategy
****************************************

.. rest_method:: POST /api/orchestration/system-config-update/strategy

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Request parameters**

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "controller-apply-type", "plain", "xsd:string", "The apply type for controller hosts: 
   ``serial`` or ``ignore``."
   "storage-apply-type", "plain", "xsd:string", "The apply type for storage hosts: 
   ``serial`` or ``ignore``."
   "worker-apply-type", "plain", "xsd:string", "The apply type for worker hosts: 
   ``serial``, ``parallel`` or ``ignore``."
   "max-parallel-worker-hosts (Optional)", "plain", "xsd:integer", 
   "The maximum number of worker hosts to patch in parallel; only applicable if 
   ``worker-apply-type = parallel``. Default value is ``2``."
   "default-instance-action", "plain", "xsd:string", "The default instance action: 
   ``stop-start`` or ``migrate``."
   "alarm-restrictions (Optional)", "plain", "xsd:string", "The strictness of alarm checks: 
   ``strict`` or ``relaxed``."

::

   {
     "controller-apply-type": "serial",
     "storage-apply-type": "ignore",
     "worker-apply-type": "serial",
     "default-instance-action": "stop-start",
     "alarm-restrictions": "strict",
   }

::

   {
     "strategy": {
       "name": "system-config-update",
       "worker-apply-type": "serial",
       "controller-apply-type": "serial",
       "swift-apply-type": "ignore",
       "storage-apply-type": "ignore",
       "current-phase-completion-percentage": 0,
       "uuid": "447c4267-0ecb-48f4-9237-1d747a3e7cca",
       "default-instance-action": "stop-start",
       "max-parallel-worker-hosts": 2,
       "alarm-restrictions": "strict",
       "state": "building",
       "build-phase": {
         "phase-name": "build",
         "current-stage": 0,
         "start-date-time": "",
         "end-date-time": "",
         "completion-percentage": 0,
         "stop-at-stage": 3,
         "result": "inprogress",
         "timeout": 182,
         "reason": "",
         "inprogress": true,
         "total-stages": 3,
         "stages": [
           {
             "stage-id": 0,
             "stage-name": "system-config-update-query",
             "total-steps": 3,
             "inprogress": true,
             "start-date-time": "",
             "end-date-time": "",
             "reason": "",
             "current-step": 0,
             "result": "inprogress",
             "timeout": 181,
             "steps": [
               {
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "success",
                 "reason": ""
               },
               {
                 "step-id": 1,
                 "step-name": "query-strategy-required",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "success",
                 "reason": ""
               },
               {
                 "step-id": 2,
                 "step-name": "query-in-sync",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "success",
                 "reason": ""
               }
             ],
           }
         ],
       },
       "apply-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "apply",
         "completion-percentage": 100,
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [],
         "current-stage": 0
       },
       "abort-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "abort",
         "completion-percentage": 100,
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress":false,
         "stages": [],
         "current-stage": 0
       }
     }
   }

**************************************************
Deletes the current system-config-update strategy
**************************************************

.. rest_method:: DELETE /api/orchestration/system-config-update/strategy

**Normal response codes**

204

::

   {
   }

**************************************************
Applies or aborts a system-config-update strategy
**************************************************

.. rest_method:: POST /api/orchestration/system-config-update/strategy/actions

**Normal response codes**

202

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Request parameters**

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "action", "plain", "xsd:string", "The action to take: ``apply-all``, ``apply-stage``, 
   ``abort`` or ``abort-stage``."
   "stage-id (Optional)", "plain", "xsd:string", "The stage-id to apply or abort. 
   Only used with ``apply-stage`` or ``abort-stage`` actions."

**Note**

* stage-id - This is used to apply or abort a particular stage in the execution flow.
  Each stage has a number specified. This can be identified from the response parameter 
  'stage-id' which can be used to apply or abort a specific stage.
* apply-all or abort-all - This is recommended option, as it takes care of applying 
  or aborting all the required stages." 

::

   {
     "action": "apply-all"
   }

::

   {
     "strategy":{
       "controller-apply-type": "serial",
       "swift-apply-type": "ignore",
       "current-phase-completion-percentage": 0,
       "uuid": "447c4267-0ecb-48f4-9237-1d747a3e7cca",
       "name": "system-config-update",
       "current-phase": "build",
       "storage-apply-type": "ignore",
       "state":"building",
       "worker-apply-type": "serial",
       "default-instance-action": "stop-start",
       "max-parallel-worker-hosts": 2,
       "alarm-restrictions": "strict",
       "build-phase": {
         "phase-name": "build",
         "current-stage": 0,
         "start-date-time": "",
         "end-date-time": "",
         "completion-percentage": 0,
         "stop-at-stage": 3,
         "result": "inprogress",
         "timeout": 182,
         "reason": "",
         "inprogress": true,
         "total-stages": 3,
         "stages": [
           {
             "stage-id": 0,
             "stage-name": "system-config-update-query",
             "total-steps": 3,
             "inprogress": true,
             "start-date-time": "",
             "end-date-time": "",
             "reason": "",
             "current-step": 0,
             "result": "inprogress",
             "timeout": 181,
             "steps": [
               {
                 "step-id": 0,
                 "step-name": "query-alarms",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "success",
                 "reason": ""
               },
               {
                 "step-id": 1,
                 "step-name": "query-strategy-required",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "success",
                 "reason": ""
               },
               {
                 "step-id": 2,
                 "step-name": "query-in-sync",
                 "entity-type": "",
                 "entity-names": [],
                 "entity-uuids": [],
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "result": "success",
                 "reason": ""
               }
             ],
           }
         ],
       },
       "apply-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "apply",
         "completion-percentage": 100,
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [],
         "current-stage": 0
       },
       "abort-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "abort",
         "completion-percentage": 100,
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [],
         "current-stage": 0
       }
     }
   }

-----------------
Current Strategy
-----------------

Current Strategy REST API shows the current active strategy
type and its corresponding state.

****************************************************************
Shows detailed information about the current active strategy
****************************************************************

.. rest_method:: GET /api/orchestration/current-strategy/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response parameters**

.. csv-table::
       :header: "Parameter", "Style", "Type", "Description"
       :widths: 20, 20, 20, 60

       "name", "plain", "xsd:string", "Strategy name."
       "state", "plain", "xsd:string", "Current state of strategy."

**Response body example**

The result shows current active strategy name and type.

::

            {
                "strategy": {
                "name": "sw-upgrade",
                "state": "applying"
                }
            }

The result shows there is no current strategy.

::

            {
                "strategy": null
            }


---------------------------------------------------------
Orchestrated Software Deployment Use Cases and Procedure
---------------------------------------------------------

Software deployment orchestration automates the process of deploying new patch releases
or major releases across all hosts of a cloud.
The orchestration supports orchestrating the deployment of both In-service and
Reboot Required Patch Releases of software and Major Releases of software.

All commands in this procedure are authenticated and require a Keystone Token in the
X-Auth-Token Header of the Request. See ‘Keystone Authentication Request’ at the top of 
this page for more details.

Commands in these procedures are from a variety of StarlingX REST API endpoints,
not just the VIM NFV endpoint; e.g. bareMetal, configuration, software,
distributedCloud endpoints are also used.


--------------------------------------------------------------------------
Software deploy Orchestration for Patch Release and Major Release Update
--------------------------------------------------------------------------

***************
Pre-requisite
***************

-----------------------------------------
Check if there is any existing strategy
-----------------------------------------

.. rest_method:: GET /api/orchestration/current-strategy/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response parameters**

.. csv-table::
       :header: "Parameter", "Style", "Type", "Description"
       :widths: 20, 20, 20, 60

       "name", "plain", "xsd:string", "Strategy name."
       "state", "plain", "xsd:string", "Current state of strategy."

**Response body example**

The result shows there is no current strategy.

::

            {
                "strategy": null
            }

**Note**
This command should take few seconds to return.
If there is an existing strategy, 'strategy-name' and 'state' would be returned.
Wait for the existing strategy to complete.

------------------------------------------------
Upload of software release on system controller
------------------------------------------------

The typical port used for Software REST API is 5497.

.. rest_method:: POST {software_url}:{software_port}/v1/release

**Request**

**Request body example**

::

           data:
              [
                "/home/sysadmin/10.0.1-software.patch"

                (or)

                "/home/sysadmin/starlingx-0.0.0.iso",
                "/home/sysadmin/starlingx-0.0.0.sig"
              ]

**Response**

**Normal response codes**

200

**Error response codes**

internalServerError (500)

**Response body parameters**

To verify if the software upload of a release is successful or not use below parameter.

* error - In case of successful upload, this is an empty string(""). On failure, 
  this will have the error message.

.. csv-table::
           :header: "Parameter", "Style", "Type", "Description"
           :widths: 20, 20, 20, 60

           "info", "plain", "xsd:string", "Any information regarding the request processing."
           "warning", "plain", "xsd:string", "Any warnings generated during the request processing."
           "error", "plain", "xsd:string", "Any errors generated during the request processing."
           "upload_info", "plain", "xsd:list", "Information regarding uploaded files."

**Response body example**

::


           {
              "error": "",
              "info": "stx-10.0.1 is now uploaded\n",
              "upload_info": [
              {
                  "10.0.1-software-insvc.patch": {
                  "id": "stx-10.0.1",
                  "sw_release": "10.0.1"
              }
           }
           ],
              "warning": ""
           }



           {
              "error": "",
              "info": "stx-10.0.1 is now uploaded\n",
              "upload_info": [
              {
                 'file.iso': {
                 'id': 'stx-0.0.0',
                 'sw_release': '0.0.0'
                  },
                 'file.sig': {
                    'id': None,
                    'sw_release': None
                    }
              }
              ],
           }

**Note**
This command can take several minutes to complete (e.g. ~ 10 mins); 
especially in the case of a Major Release ISO.
Patch files are typically much smaller and faster to load, e.g. a minute or less.
There is no mechanism to monitor progress.
The RESTAPI Response is not sent until the command completes.

-------------------------------------------
DC - Prestage software release on subcloud
-------------------------------------------

Create prestage-strategy is used in case of Distributed Cloud environment(DC),
to make the software release available on the subcloud.
The typical port used for dcmanager REST API is 8119.

.. rest_method:: POST {dcmanager_url}:{dcmanager_port}/v1.0/sw-update-strategy/

**Request**

**Request body parameters**
    
* subcloud-apply-type: subcloud_name
* max-parallel-subclouds: max_parallel_subclouds
* stop-on-failure: stop_on_failure
* cloud-name: name_of_cloud
* type: sw_update_strategy_type
* sysadmin_password: password
* for_sw_deploy: true
* prestage-software-version: YY.MM/YY.MM.nn
        
**Request body example**

::

       {
         "type": "prestage",
         "cloud_name": "subcloud1",
         "sysadmin_password": "TGk2OW51eCoxMjM0",
         "for_sw_deploy": True,
         "prestage-software-version": "10.0"
       }

**Response**

**Normal response codes**

200

**Error response codes**

badRequest (400), unauthorized (401), forbidden (403), badMethod (405),
HTTPUnprocessableEntity (422), internalServerError (500),
serviceUnavailable (503)

**Response parameters**

.. csv-table::
           :header: "Parameter", "Type", "Description"
           :widths: 20, 20, 90

           "type", "xsd:string", "Filter to query a particular type of update strategy 
           if it exists. One of: firmware, kube-rootca-update, kubernetes, patch, prestage, 
           or sw-deploy."
           "subcloud-apply-type", "xsd:string", "The apply type for the update. serial 
           or parallel."
           "max-parallel-subclouds", "xsd:integer", "The maximum number of subclouds 
           to update in parallel."
           "stop-on-failure", "xsd:boolean", "Flag to indicate if the update should 
           stop updating additional subclouds if a failure is encountered."
           "state", "xsd:integer", "The internal state of the sw-update-strategy."
           "prestage_software_version", "xsd:integer", "The prestage software version for 
           the subcloud."

**Note**
In case of create prestage strategy , the strategy response would be in 'initial' state on
successful creation of prestage-strategy. On failure, there would not be any strategy created
and error response will be returned.

**Response body example**

::

     {
       strategy type: prestage
       subcloud apply type: None
       max parallel subclouds: 2
       stop on failure:False
       prestage software version: 10.0
       state: initial
     }

------------------------------
DC - Apply prestage-strategy
------------------------------

Apply prestage strategy is used in case of Distributed Cloud environment(DC),
to make the software release available on the subcloud.

.. rest_method:: POST {dcmanager_url}:{dcmanager_port}/v1.0/sw-update-strategy/actions?type=prestage

**Request**

**Request body parameters**

* subcloud-apply-type: subcloud_name
* stop-on-failure: stop_on_failure
* cloud-name: name_of_cloud
* type: sw_update_strategy_type
* sysadmin_password: password
* for_sw_deploy: true
* prestage-software-version: YY.MM/YY.MM.nn
* action: action_to_perform

**Request body example**

::

       {
         "type": "prestage",
         "cloud_name": "subcloud1",
         "sysadmin_password": "TGk2OW51eCoxMjM0",
         "for_sw_deploy": True,
         "prestage-software-version": "10.0",
         "action": "apply"
       }

**Response**

**Normal response codes**

200

**Error response codes**

badRequest (400), unauthorized (401), forbidden (403), badMethod (405),
HTTPUnprocessableEntity (422), internalServerError (500),
serviceUnavailable (503)

**Response parameters**

.. csv-table::
           :header: "Parameter", "Type", "Description"
           :widths: 20, 20, 60

           "type", "xsd:string", "Filter to query a particular type of update strategy
           if it exists. One of: firmware, kube-rootca-update, kubernetes, patch, prestage, 
           or sw-deploy."
           "subcloud-apply-type", "xsd:string", "The apply type for the update. serial
           or parallel."
           "max-parallel-subclouds", "xsd:integer", "The maximum number of subclouds
           to update in parallel."
           "stop-on-failure", "xsd:boolean", "Flag to indicate if the update should
           stop updating additional subclouds if a failure is encountered."
           "state", "xsd:integer", "The internal state of the sw-update-strategy."
           "prestage_software_version", "xsd:integer", "The prestage software version for 
           the subcloud."

**Note**
On applying a prestage strategy , below are the different 'state' that can be seen.

* 'completed' - strategy applied successfully.
* 'applying' - strategy apply in progress.
* 'aborted' or 'failed' - strategy apply failed.

**Response body example**

::

     {
       strategy type: prestage
       subcloud apply type: None
       max parallel subclouds: 2
       stop on failure:False
       prestage software version: 10.0
       state: applying
     }

------
Steps
------

-----------------------------
1) Create sw-deploy-strategy
-----------------------------

Creates software deploy strategy

.. rest_method:: POST /api/orchestration/sw-upgrade/strategy

**Request**

**Request parameters**

.. csv-table::
            :header: "Parameter", "Style", "Type", "Description"
            :widths: 20, 20, 20, 60

            "storage-apply-type", "plain", "xsd:string", "The apply type for storage hosts:
            ``serial``, ``parallel`` or ``ignore``."
            "worker-apply-type", "plain", "xsd:string", "The apply type for worker hosts: ``serial``, 
            ``parallel`` or ``ignore``."
            "max-parallel-worker-hosts (Optional)", "plain", "xsd:integer", "The maximum number of 
            worker hosts to upgrade in parallel; only applicable if ``worker-apply-type = parallel``.
            Default value is ``2``."
            "alarm-restrictions (Optional)", "plain", "xsd:string", "The strictness of alarm checks:
            ``strict`` or ``relaxed``."
            "release", "plain", "xsd:string", "The release identification name."
            "rollback", "plain", "xsd:bool", "The flag that indicates this is a rollback action."
            "delete", "plain", "xsd:bool", "The flag that indicates that deployment will be 
            marked complete."

**Request body example**

::

          {
             "controller-apply-type": "serial/ignore",
             "default-instance-action": "stop-start/migrate",
             "release": "stx-10.0.1",
             "rollback": false,
             "delete": true,
             "storage-apply-type": "serial/ignore",
             "worker-apply-type": "serial/parallel/ignore",
             "alarm-restrictions": "strict/relaxed"
          }

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Response parameters**

The "sw-deploy create strategy" request starts the creation process of the strategy, 
and returns a response to indicate the status of the creation process. 
E.g. typically after initially starting the create.

* state ='building'.
* current-phase ='build'

Use the sw-deploy get strategy request to monitor the progress and status of the create.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the 
   reason for failure,if any."

**Response body example**

::

            {
                "strategy": {
                  "controller-apply-type": "serial",
                  "current-phase-completion-percentage": 0,
                  "uuid": "ac9b953a-caf1-4abe-8d53-498b598e6731",
                  "release-id": "stx-10.0.1",
                  "worker-apply-type": "serial",
                  "storage-apply-type": "serial",
                  "max-parallel-worker-hosts": 2,
                  "current-phase": "build",
                  "apply-phase": {
                  "start-date-time": "",
                  "end-date-time": "",
                  "phase-name": "apply",
                  "completion-percentage": 100,
                  "total-stages": 0,
                  "stop-at-stage": 0,
                  "result": "initial",
                  "timeout": 0,
                  "reason": "",
                  "inprogress": false,
                  "stages": [],
                  "current-stage": 0,
                  },
                  "storage-apply-type": "serial",
                  "state": "building",
                  "default-instance-action": "migrate",
                  "alarm-restrictions": "relaxed",
                  "abort-phase": {
                  "start-date-time": "",
                  "end-date-time": "",
                  "phase-name": "abort",
                  "completion-percentage": 100,
                  "total-stages": 0,
                  "stop-at-stage": 0,
                  "result": "initial",
                  "timeout": 0,
                  "reason": "",
                  "inprogress": false,
                  "stages": [],
                  "current-stage": 0
                  }
               }
            }

**Note**
The execution will take few seconds to return the result.
The progress can be monitored using step 2.

-----------------------------
2) Show the strategy details
-----------------------------

Shows the active strategy details.

.. rest_method:: GET /api/orchestration/sw-upgrade/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response parameters**

The details of the strategy can be checked using below response parameter.

* state - 'building or applying or aborting' or 'ready-to-apply or applied 
  or aborted' or 'build-failed or apply-failed or abort-failed'.
* result - 'success' or 'failed' or 'aborted'.
* reason and response - It's empty "" on success and on failure it's updated 
  with details of error.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the 
   reason for failure,if any."

**Note**

* Phase - This refers to 'create or apply or abort' phase of strategy
* Stage - This points to various stages at each phase.Example; 'sw-upgrade start deploy', 
  'sw-upgrade deploy host'
* Step - This refers to different steps executed in each stage. 
  Example; In 'sw-upgrade deploy host' stage, there are different steps like lock-hosts, 
  upgrade-hosts, system-stabilize, unlock-hosts.

When using this API to monitor the progress or status of a create, apply or abort
operation, wait for the 'completion-percentage' parameter to reach 100%.
The 'completion-percentage' is 100% only in success case.
Then, use the 'result' parameter to determine whether it indicates
'success' or 'failure'. In the failure scenario, the 'reason' and 'response'
parameters provide more detailed information related to the failure.

**Response body example**

::

          {
               "completion-percentage": 100%
               "state": "ready-to-apply"
          }

Create phase is considered as completed if above values are set
in response message.

----------------------------
3) Apply sw-deploy-strategy
----------------------------

.. rest_method:: POST /api/orchestration/sw-upgrade/strategy/actions

**Request**

**Request body parameters**

.. csv-table::
           :header: "Parameter", "Style", "Type", "Description"
           :widths: 20, 20, 20, 60

           "action", "plain", "xsd:string", "The action to take: ``apply-all``, ``apply-stage``,
           ``abort`` or ``abort-stage``."
           "stage-id (Optional)", "plain", "xsd:string", "The stage-id to apply or abort.
           Only used with ``apply-stage`` or ``abort-stage`` actions."

**Note**

* stage-id - This is used to apply or abort a particular stage in the execution flow.
  Each stage has a number specified. This can be identified from the response parameter 
  'stage-id' which can be used to apply or abort a specific stage.
* apply-all or abort-all - This is recommended option, as it takes care of applying 
  or aborting all the required stages." 

**Request body example**

::

           {
             "action": "apply-all"
           }

**Response**

**Normal response codes**

202

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Response parameters**

The "sw-deploy" strategy "apply" or "abort" request starts the apply or abort process, 
and returns a response to indicate the current status of the apply or abort process. 
E.g. typically after initially starting the create.

* state = 'applying' or 'aborting'.
* current-phase ='apply' or 'abort'

Use the sw-deploy get strategy request to monitor the progress and status of Apply strategy.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the 
   reason for failure,if any."

**Response body example**

::

            {
              "strategy": {
              "controller-apply-type": "serial",
              "current-phase-completion-percentage": 0,
              "uuid": "ac9b953a-caf1-4abe-8d53-498b598e6731",
              "name": "sw-upgrade",
              "worker-apply-type": "serial",
              "max-parallel-worker-hosts": 2,
              "current-phase": "apply",
              "apply-phase": {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "phase-name": "apply",
              "completion-percentage": 0,
              "total-stages": 3,
              "stop-at-stage": 3,
              "result": "inprogress",
              "timeout": 18304,
              "reason": "",
              "response": ""
              "inprogress": true,
              "stages": [
              {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "stage-id": 0,
              "reason": "",
              "current-step": 0,
              "steps": [
              {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "timeout": 60,
              "entity-type": "",
              "step-id": 0,
              "entity-uuids": [],
              "step-name": "query-alarms",
              "result": "wait",
              "entity-names": [],
              "reason": ""
              }
            }
          

**Note**
The API takes long time to complete the operation. Approximately it takes an hour
(depending on number of host configured).

------------------------------------------
4) Apply strategy with stage-id(Optional)
------------------------------------------

If a particular stage needs to be applied, then use the stage id parameter.
To identify the stage-id that needs to be applied, the user can get the details by looking
for stage-id data in the strategy output.

.. rest_method:: POST /api/orchestration/sw-upgrade/strategy/actions

**Request**

**Request body parameters**

.. csv-table::
           :header: "Parameter", "Style", "Type", "Description"
           :widths: 20, 20, 20, 60

           "action", "plain", "xsd:string", "The action to take: ``apply-all``,
           ``apply-stage``,``abort``or ``abort-stage``."
           "stage-id (Optional)", "plain", "xsd:string", "The stage-id to apply or abort.
           Only used with ``apply-stage`` or ``abort-stage`` actions."

**Note**

* stage-id - This is used to apply or abort a particular stage in the execution flow.
  Each stage has a number specified. This can be identified from the response parameter 
  'stage-id' which can be used to apply or abort a specific stage.
* apply-all or abort-all - This is recommended option, as it takes care of applying 
  or aborting all the required stages."

**Request body example**

::

           {
             "action": "apply-stage",
             "stage-id": "2"
           }

**Response**

**Normal response codes**

202

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Response parameters**

The "sw-deploy" strategy "apply" or "abort" request starts the apply or abort process, 
and returns a response to indicate the current status of the apply or abort process. 
E.g. typically after initially starting the create.

* state = 'applying' or 'aborting'.
* current-phase ='apply' or 'abort'

Use the sw-deploy get strategy request to monitor the progress and status of Apply strategy.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the 
   reason for failure,if any."

**Response body example**

::

            {
              "strategy": {
              "controller-apply-type": "serial",
              "current-phase-completion-percentage": 0,
              "uuid": "ac9b953a-caf1-4abe-8d53-498b598e6731",
              "name": "sw-upgrade",
              "worker-apply-type": "serial",
              "max-parallel-worker-hosts": 2,
              "current-phase": "apply",
              "apply-phase": {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "phase-name": "apply",
              "completion-percentage": 0,
              "total-stages": 3,
              "stop-at-stage": 3,
              "result": "inprogress",
              "timeout": 18304,
              "reason": "",
              "inprogress": true,
              "stages": [
              {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "stage-id": 0,
              "reason": "",
              "current-step": 0,
              "steps": [
              {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "timeout": 60,
              "entity-type": "",
              "step-id": 0,
              "entity-uuids": [],
              "step-name": "query-alarms",
              "result": "wait",
              "entity-names": [],
              "reason": ""
              }
             }
            }

-------------------------------------------------------------------------------------
5) Check the progress of the apply phase using below API and wait for it to complete
-------------------------------------------------------------------------------------

The apply phase is considered to be completed if below values are set.


.. rest_method:: GET /api/orchestration/sw-upgrade/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response parameters**

The details of the strategy can be checked using below response parameter.

* state - 'building or applying or aborting' or 'ready-to-apply or 
  applied or aborted' or 'build-failed or apply-failed or abort-failed'.
* result - 'success' or 'failed' or 'aborted'.
* reason and response - It's empty "" on success and on failure it's updated 
  with details of error.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the 
   reason for failure,if any."

**Note**

* Phase - This refers to 'create or apply or abort' phase of strategy
* Stage - This points to various stages at each phase.Example; 
  'sw-upgrade start deploy', 'sw-upgrade deploy host'
* Step - This refers to different steps executed in each stage. 
  Example; In 'sw-upgrade deploy host' stage, there are different steps like lock-hosts, 
  upgrade-hosts, system-stabilize, unlock-hosts.

When using this API to monitor the progress or status of a create, apply or abort
operation, wait for the 'completion-percentage' parameter to reach 100%.
The 'completion-percentage' is 100% only in success case.
Then, use the 'result' parameter to determine whether it indicates
'success' or 'failure'. In the failure scenario, the 'reason' and 'response'
parameters provide more detailed information related to the failure.

**Response body example**

::

          {
               "completion-percentage": 100%
               "state": "applied",
               "result": success,
               "reason": "",
               "response": "",
          }

------------------
6) Post-requisite
------------------

If the user has not selected ‘delete: true’ in step 1, then complete the deployment
using below API to delete.
The typical port used for software REST API is 5497.

.. rest_method:: DELETE {software_url}:{software_port}/v1/deploy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

internalServerError (500)

**Response parameters**

.. csv-table::
       :header: "Parameter", "Style", "Type", "Description"
       :widths: 20, 20, 20, 60

       "info", "plain", "xsd:string", "Any information regarding the request processing."
       "warning", "plain", "xsd:string", "Any warnings generated during the request processing."
       "error", "plain", "xsd:string", "Any errors generated during the request processing."

**Response body example**

::

      {
          "info": "Deploy deleted with success",
          "warning": "",
          "error": ""
      }

This will mark the deployment complete.

--------------------------------------------------------
Software deploy Orchestration for Patch Release Removal
--------------------------------------------------------

A fully deployed patch release can be removed (or un-deployed) by using the
orchestration strategy and deploying a previous patch release.

**Note**
Software deployment orchestration supports only Patch release removal.
Major release downgrade is not supported.

**************
Pre-requisite
**************

Check for all the pre-requisites mentioned in 'pre-requisite' section of
'Software deployment Orchestration for Patch Release and Major Release Update' in 
addition to the below pre-requisites.

---------------------------------------
Check if current strategy is existing
---------------------------------------

.. rest_method:: GET /api/orchestration/current-strategy/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response parameters**

.. csv-table::
       :header: "Parameter", "Style", "Type", "Description"
       :widths: 20, 20, 20, 60

       "name", "plain", "xsd:string", "Strategy name."
       "state", "plain", "xsd:string", "Current state of strategy."

**Response body example**

The result shows there is no current strategy.

::

            {
                "strategy": null
            }

---------------------
Shows software list
---------------------

The typical port used for the Software REST API is 5497.
Software list shows the release is in ‘deployed’ state.

.. rest_method:: GET {software_url}:{software_port}/v1/release/{release-id}

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

internalServerError (500)

**Response body parameter**

.. csv-table::
       :header: "Parameter", "Style", "Type", "Description"
       :widths: 20, 20, 20, 60

       "release_id", "plain", "xsd:string", "The release identification name."
       "state", "plain", "xsd:string", "The current release state."
       "sw_version", "plain", "xsd:string", "The software version for which the deploy is intended."
       "component", "plain", "xsd:string", "The component present in the release."
       "status", "plain", "xsd:string", "The status of the release."
       "unremovable", "plain", "xsd:string", "The flag that indicates if release is unremovable."
       "summary", "plain", "xsd:string", "A brief summary of the release."
       "description", "plain", "xsd:string", "The description of any updates present in this release."
       "install_instructions", "plain", "xsd:string", "Instructions on how to install the release."
       "warnings", "plain", "xsd:string", "Any warnings associated with the usage of the release."
       "reboot_required", "plain", "xsd:bool", "The flag that indicates if release is reboot required."
       "prepatched_iso", "plain", "xsd:bool", "The flag that indicates if release is a prepatched iso."
       "requires", "plain", "xsd:list", "A list of patch ids required for this patch release to be installed."
       "packages", "plain", "xsd:list", "A list of packages present in the release."

**Response body example**

::

        {
           "release_id":"stx-0.0.0",
           "state":"deployed",
           "sw_version":"0.0.0",
           "component":null,
           "status":"REL",
           "unremovable":true,
           "summary":"STX 0.0 GA release",
           "description":"STX 0.0 major GA release",
           "install_instructions":"",
           "warnings":"",
           "reboot_required": true,
           "prepatched_iso": true,
           "requires":[
           ],
           "packages":[
           ]
        }

------
Steps
------
-----------------------------
1) Create sw-deploy-strategy
-----------------------------

Create software deploy strategy.

.. rest_method:: POST /api/orchestration/sw-upgrade/strategy

**Request**

**Request parameters**

.. csv-table::
            :header: "Parameter", "Style", "Type", "Description"
            :widths: 20, 20, 20, 60

            "storage-apply-type", "plain", "xsd:string", "The apply type for storage hosts:
            ``serial``, ``parallel`` or ``ignore``."
            "worker-apply-type", "plain", "xsd:string", "The apply type for worker hosts: ``serial``, 
            ``parallel`` or ``ignore``."
            "max-parallel-worker-hosts (Optional)", "plain", "xsd:integer", "The maximum number of 
            worker hosts to upgrade in parallel; only applicable if ``worker-apply-type = parallel``.
            Default value is ``2``."
            "alarm-restrictions (Optional)", "plain", "xsd:string", "The strictness of alarm checks:
            ``strict`` or ``relaxed``."
            "release", "plain", "xsd:string", "The release identification name."
            "rollback", "plain", "xsd:bool", "The flag that indicates this is a rollback action."
            "delete", "plain", "xsd:bool", "The flag that indicates that deployment will be marked complete."

**Request body example**

::

          {
             "controller-apply-type": "serial/ignore",
             "default-instance-action": "stop-start/migrate",
             "release": "stx-10.0.1",
             "rollback": false,
             "delete": true,
             "storage-apply-type": "serial/ignore",
             "worker-apply-type": "serial/parallel/ignore",
             "alarm-restrictions": "strict/relaxed"
          }

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Response parameters**

The "sw-deploy create strategy" request starts the creation process of the strategy, 
and returns a response to indicate the status of the creation process. 
E.g. typically after initially starting the create.

* state ='building'.
* current-phase ='build'

Use the sw-deploy get strategy request to monitor the progress and status of the create.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the reason 
   for failure,if any."

**Response body example**

::

            {
                "strategy": {
                  "controller-apply-type": "serial",
                  "current-phase-completion-percentage": 0,
                  "uuid": "ac9b953a-caf1-4abe-8d53-498b598e6731",
                  "release-id": "stx-10.0.1",
                  "worker-apply-type": "serial",
                  "storage-apply-type": "serial",
                  "max-parallel-worker-hosts": 2,
                  "current-phase": "build",
                  "apply-phase": {
                  "start-date-time": "",
                  "end-date-time": "",
                  "phase-name": "apply",
                  "completion-percentage": 100,
                  "total-stages": 0,
                  "stop-at-stage": 0,
                  "result": "initial",
                  "timeout": 0,
                  "reason": "",
                  "inprogress": false,
                  "stages": [],
                  "current-stage": 0,
                  },
                  "storage-apply-type": "serial",
                  "state": "building",
                  "default-instance-action": "migrate",
                  "alarm-restrictions": "relaxed",
                  "abort-phase": {
                  "start-date-time": "",
                  "end-date-time": "",
                  "phase-name": "abort",
                  "completion-percentage": 100,
                  "total-stages": 0,
                  "stop-at-stage": 0,
                  "result": "initial",
                  "timeout": 0,
                  "reason": "",
                  "inprogress": false,
                  "stages": [],
                  "current-stage": 0
                  }
              }
            }

**Note**
The execution will take few seconds to return the result.
The progress can be monitered using step 2.

-----------------------------
2) Show the strategy details
-----------------------------

Shows the active strategy details.

.. rest_method:: GET /api/orchestration/sw-upgrade/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response parameters**

The details of the strategy can be checked using below response parameter.

* state - 'building or applying or aborting' or 'ready-to-apply or 
  applied or aborted' or 'build-failed or apply-failed or abort-failed'.
* result - 'success' or 'failed' or 'aborted'.
* reason and response - It's empty "" on success and on failure it's updated 
  with details of error.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the 
   reason for failure,if any."

**Note**

* Phase - This refers to 'create or apply or abort' phase of strategy
* Stage - This points to various stages at each phase.
  Example; 'sw-upgrade start deploy', 'sw-upgrade deploy host'
* Step - This refers to different steps executed in each stage. 
  Example; In 'sw-upgrade deploy host' stage, there are different steps like lock-hosts, 
  upgrade-hosts, system-stabilize, unlock-hosts.

When using this API to monitor the progress or status of a create, apply or abort
operation, wait for the 'completion-percentage' parameter to reach 100%.
The 'completion-percentage' is 100% only in success case.
Then, use the 'result' parameter to determine whether it indicates
'success' or 'failure'. In the failure scenario, the 'reason' and 'response'
parameters provide more detailed information related to the failure.

**Response body example**

::

          {
               "current-phase-completion": 100%
               "state": "ready-to-apply"
          }

Create phase is considered as completed if above values are set
in response message.

----------------------------
3) Apply sw-deploy-strategy
----------------------------

.. rest_method:: POST /api/orchestration/sw-upgrade/strategy/actions

**Request**

**Request body parameters**

.. csv-table::
           :header: "Parameter", "Style", "Type", "Description"
           :widths: 20, 20, 20, 60

           "action", "plain", "xsd:string", "The action to take: ``apply-all``, ``apply-stage``,
           ``abort`` or ``abort-stage``."
           "stage-id (Optional)", "plain", "xsd:string", "The stage-id to apply or abort.
           Only used with ``apply-stage`` or ``abort-stage`` actions."

**Note**

* stage-id - This is used to apply or abort a particular stage in the execution flow.
  Each stage has a number specified. This can be identified from the response parameter 
  'stage-id' which can be used to apply or abort a specific stage.
* apply-all or abort-all - This is recommended option, as it takes care of applying 
  or aborting all the required stages."

**Request body example**

::

           {
             "action": "apply-all"
           }

**Response**

**Normal response codes**

202

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Response parameters**

The "sw-deploy" strategy "apply" or "abort" request starts the apply or abort process, 
and returns a response to indicate the current status of the apply or abort process. 
E.g. typically after initially starting the create.

* state = 'applying' or 'aborting'.
* current-phase ='apply' or 'abort'

Use the sw-deploy get strategy request to monitor the progress and status of Apply strategy.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the 
   reason for failure,if any."

**Response body example**

::

            {
              "strategy": {
              "controller-apply-type": "serial",
              "current-phase-completion-percentage": 0,
              "uuid": "ac9b953a-caf1-4abe-8d53-498b598e6731",
              "name": "sw-upgrade",
              "worker-apply-type": "serial",
              "max-parallel-worker-hosts": 2,
              "current-phase": "apply",
              "apply-phase": {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "phase-name": "apply",
              "completion-percentage": 0,
              "total-stages": 3,
              "stop-at-stage": 3,
              "result": "inprogress",
              "timeout": 18304,
              "reason": "",
              "inprogress": true,
              "stages": [
              {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "stage-id": 0,
              "reason": "",
              "current-step": 0,
              "steps": [
              {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "timeout": 60,
              "entity-type": "",
              "step-id": 0,
              "entity-uuids": [],
              "step-name": "query-alarms",
              "result": "wait",
              "entity-names": [],
              "reason": ""
              }
             }
            }


**Note**
The API takes long time to complete the operation. Approximately it takes an hour
(depending on number of host configured).

------------------------------------------
4) Apply strategy with stage-id(Optional)
------------------------------------------

If a particular stage needs to be applied, then use the stage id parameter.
To identify the stage-id that needs to be applied, the user can get the details 
by looking for stage-id data in the strategy output.

.. rest_method:: POST /api/orchestration/sw-upgrade/strategy/actions

**Request**

**Request body parameters**

.. csv-table::
           :header: "Parameter", "Style", "Type", "Description"
           :widths: 20, 20, 20, 60

           "action", "plain", "xsd:string", "The action to take: ``apply-all``, ``apply-stage``,
           ``abort`` or ``abort-stage``."
           "stage-id (Optional)", "plain", "xsd:string", "The stage-id to apply or abort.
           Only used with ``apply-stage`` or ``abort-stage`` actions."

**Note**

* stage-id - This is used to apply or abort a particular stage in the execution flow.
  Each stage has a number specified. This can be identified from the response parameter 
  'stage-id' which can be used to apply or abort a specific stage.
* apply-all or abort-all - This is recommended option, as it takes care of applying 
  or aborting all the required stages."

**Request body example**

::

           {
             "action": "apply-stage",
             "stage-id": "2"
           }

**Response**

**Normal response codes**

202

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Response parameters**

The "sw-deploy" strategy "apply" or "abort" request starts the apply or abort process, 
and returns a response to indicate the current status of the apply or abort process. 
E.g. typically after initially starting the create.

* state = 'applying' or 'aborting'.
* current-phase ='apply' or 'abort'

Use the sw-deploy get strategy request to monitor the progress and status of Apply strategy.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the reason 
   for failure,if any."

**Response body example**

::

            {
              "strategy": {
              "controller-apply-type": "serial",
              "current-phase-completion-percentage": 0,
              "uuid": "ac9b953a-caf1-4abe-8d53-498b598e6731",
              "name": "sw-upgrade",
              "worker-apply-type": "serial",
              "max-parallel-worker-hosts": 2,
              "current-phase": "apply",
              "apply-phase": {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "phase-name": "apply",
              "completion-percentage": 0,
              "total-stages": 3,
              "stop-at-stage": 3,
              "result": "inprogress",
              "timeout": 18304,
              "reason": "",
              "inprogress": true,
              "stages": [
              {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "stage-id": 0,
              "reason": "",
              "current-step": 0,
              "steps": [
              {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "timeout": 60,
              "entity-type": "",
              "step-id": 0,
              "entity-uuids": [],
              "step-name": "query-alarms",
              "result": "wait",
              "entity-names": [],
              "reason": ""
              }
             }
            }

---------------------------
5) Show sw-deploy-strategy
---------------------------

.. rest_method:: GET /api/orchestration/sw-upgrade/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response parameters**

The details of the strategy can be checked using below response parameter.

* state - 'building or applying or aborting' or 'ready-to-apply or 
  applied or aborted' or 'build-failed or apply-failed or abort-failed'.
* result - 'success' or 'failed' or 'aborted'.
* reason and response - It's empty "" on success and on failure it's updated 
  with details of error.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the reason 
   for failure,if any."

**Note**

* Phase - This refers to 'create or apply or abort' phase of strategy
* Stage - This points to various stages at each phase.
  Example; 'sw-upgrade start deploy', 'sw-upgrade deploy host'
* Step - This refers to different steps executed in each stage. 
  Example; In 'sw-upgrade deploy host' stage, there are different steps like lock-hosts, 
  upgrade-hosts, system-stabilize, unlock-hosts.

When using this API to monitor the progress or status of a create, apply or abort
operation, wait for the 'completion-percentage' parameter to reach 100%.
The 'completion-percentage' is 100% only in success case.
Then, use the 'result' parameter to determine whether it indicates
'success' or 'failure'. In the failure scenario, the 'reason' and 'response'
parameters provide more detailed information related to the failure.

**Response body example**

::

            {
               "strategy": {
                  "current-phase-completion": "100%",
                  "state": "applied",
                }
            }

The apply phase is considered to be completed if above values are set.

------------------
6) Post-requisite
------------------

If the user has not selected ‘delete: true’ in step 1, then complete the deployment
using below API to delete.
The typical port used for software REST API is 5497.

.. rest_method:: DELETE {software_url}:{software_port}/v1/deploy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

internalServerError (500)

**Response parameters**

.. csv-table::
       :header: "Parameter", "Style", "Type", "Description"
       :widths: 20, 20, 20, 60

       "info", "plain", "xsd:string", "Any information regarding the request processing."
       "warning", "plain", "xsd:string", "Any warnings generated during the request processing."
       "error", "plain", "xsd:string", "Any errors generated during the request processing."

**Response body example**

::

      {
          "info": "Deploy deleted with success",
          "warning": "",
          "error": ""
      }

This will mark the deployment complete.

-----------------------------------------------------------------------
Software deployment Orchestration For Patch and Major Release Rollback
-----------------------------------------------------------------------

Orchestrated rollback can be performed by aborting an ongoing deployment or
if there is a failure encountered during deployment of Patch/Major release.

**Note**
Patch release Rollback is supported only in AIO-SX currently.
Orchestrated Major Release Rollback is supported only in AIO-SX currently.
Performing major release rollback is not possible during activation
or after activation(the rollback of major release in this case is
via Restore of a Backup).

***************
Pre-requisite
***************
----------------------------------------------
Check if existing strategy is in failed state
----------------------------------------------

.. rest_method:: GET /api/orchestration/current-strategy/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response body example**

The strategy can be in 'failed' or 'aborted' or 'timed-out' state.
The result shows current active strategy name and state as 'failed'.

::

            {
                "strategy": {
                "name": "sw-upgrade",
                "state": "apply-failed"
                }
            }


**Note**
If a strategy is in failed/aborted/timed-out state, check the "reason" and "response"
message fields of the failed strategy. Refer section 'Shows detailed information about the
current sw-deploy strategy' to get details of the reason for failure.

---------------------
Check System Health
---------------------

The typical port used for SYSINV API is 6385.

.. rest_method:: GET {sysinv_url}:{sysinv_port}/v1/health/

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

computeFault (400, 500, ...), serviceUnavailable (503), badRequest (400),
unauthorized (401), forbidden (403), badMethod (405), overLimit (413),
itemNotFound (404)

**Response body example**

::

            {
               "System Health":
               {
                   "All hosts are provisioned": [OK],
                   "All hosts are unlocked/enabled": [Fail],
                   "Locked or disabled hosts": controller-1,
                   "All hosts have current configurations": [OK],
                   "All hosts are patch current": [OK],
                   "Ceph Storage Healthy": [Fail],
                   "No alarms": [Fail][19] alarms found, [16] of which are 
                    management affecting and [0] are certificate expiration alarms. 
                    Use "fm alarm-list" for details
                   "All kubernetes nodes are ready": [OK]
                   "All kubernetes control plane pods are ready": [OK]
               }
            }

**Note**
The system is not in healthy state.
Example, the host may be in locked or unavailable
state.

------------------
Check for alarms
------------------

The typical port used for the FM REST API is 18002.

.. rest_method:: GET {fm_url}:{fm_port}/v1/alarms

The supported query options are alarm_id, entity_type_id,
entity_instance_id, severity and alarm_type.

**Request**

**Request parameters**

.. csv-table::
       :header: "Parameter", "Style", "Type", "Description"
       :widths: 20, 20, 20, 60

       "include_suppress (Optional)", "query", "xsd:boolean", "This optional parameter when set 
       to true (include_suppress=true)
       specifies to include suppressed alarms in output."
       "expand (Optional)", "query", "xsd:boolean", "This optional parameter when set to 
       true (expand=true) specifies that the response should contains the same response 
       parameters as when querying for a specific alarm."

**Response**

**Normal response codes**

200

**Error response codes**

computeFault (400, 500, ...), serviceUnavailable (503), badRequest (400),
unauthorized (401), forbidden (403), badMethod (405), overLimit (413),
itemNotFound (404)

**Response body parameters**

.. csv-table::
           :header: "Parameter", "Style", "Type", "Description"
           :widths: 20, 20, 20, 60

           "alarms (Optional)", "plain", "xsd:list", "The list of active alarms based on 
           the specified query."
           "alarm_id (Optional)", "plain", "xsd:string", "The alarm ID; each type of alarm 
           has a unique ID.Note the alarm_id and the entity_instance_id uniquely identify an 
           alarm instance."
           "entity_instance_id (Optional)", "plain", "xsd:string", "The instance of the object 
           raising alarm. A .separated list of sub-entity-type=instance-value pairs, 
           representing the containment structure of the overall entity instance. 
           Note the alarm_id and the entity_instance_id uniquely identify an alarm instance."
           "reason_text (Optional)", "plain", "xsd:string", "The text description of the alarm."
           "severity (Optional)", "plain", "xsd:string", "The severity of the alarm; ``critical``, 
           ``major``,``minor``, or ``warning``."
           "timestamp (Optional)", "plain", "xsd:dateTime", "The time in UTC at which the alarm 
           has last been updated."
           "uuid (Optional)", "plain", "csapi:UUID", "The unique identifier of the alarm."

**Responde body example**
        
::

           {
             "alarms":[
             {
                "severity":"major",
                "timestamp":"2016-05-12T12:11:10.405609",
                "uuid":"25d28c97-70e4-45c7-a896-ba8e71a81f26",
                "alarm_id":"400.002",
                "entity_instance_id":"service_domain=controller.service_group=oam-services",
                "suppression_status":"suppressed",
                "reason_text":"Service group oam-services loss of redundancy;
                expected 1 standby member but no standby members available",
                "mgmt_affecting": "warning"
             }
           }


**Note**
Active alarm(s) may be present as the system might be in
locked, unavailable state.

------
Steps
------
--------------------------------------
1) Delete existing sw-deploy-strategy
--------------------------------------

.. rest_method:: DELETE /api/orchestration/sw-upgrade/strategy/

**Request**

**Request body parameter**
       
::

          {
             "force": false
          }

**Response**

**Normal response codes**

204

**Response body example**

::

           {
           }

------------------------------------------
2) Create new rollback sw-deploy-strategy
------------------------------------------

.. rest_method:: POST /api/orchestration/sw-upgrade/strategy

**Request**

**Request parameters**

The "sw-deploy create strategy" request starts the creation process of the strategy, 
and returns a response to indicate the status of the creation process. 
E.g. typically after initially starting the create.

* state ='building'.
* current-phase ='build'

Use the sw-deploy get strategy request to monitor the progress and status of the create.

.. csv-table::
            :header: "Parameter", "Style", "Type", "Description"
            :widths: 20, 20, 20, 60

            "storage-apply-type", "plain", "xsd:string", "The apply type for storage hosts:
            ``serial``, ``parallel`` or ``ignore``."
            "worker-apply-type", "plain", "xsd:string", "The apply type for worker hosts: ``serial`` , 
            ``parallel`` or ``ignore``."
            "max-parallel-worker-hosts (Optional)", "plain", "xsd:integer", "The maximum number 
            of worker hosts to upgrade in parallel; only applicable if ``worker-apply-type = 
            parallel``. Default value is ``2``."
            "alarm-restrictions (Optional)", "plain", "xsd:string", "The strictness of alarm 
            checks:``strict`` or ``relaxed``."
            "release", "plain", "xsd:string", "The release identification name."
            "rollback", "plain", "xsd:bool", "The flag that indicates this is a rollback action."
            "delete", "plain", "xsd:bool", "The flag that indicates that deployment will be marked complete."


**Request body example**

::

          {
             "controller-apply-type": "serial/ignore",
             "default-instance-action": "stop-start/migrate",
             "release": null,
             "rollback": true,
             "delete": null,
             "storage-apply-type": "serial/ignore",
             "worker-apply-type": "serial/parallel/ignore",
             "alarm-restrictions": "strict/relaxed"
          }


---------------------------
3) Show sw-deploy strategy
---------------------------

Shows the active strategy details.

.. rest_method:: GET /api/orchestration/sw-upgrade/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response parameters**

The details of the strategy can be checked using below response parameter.

* state - 'building or applying or aborting' or 'ready-to-apply or 
  applied or aborted' or 'build-failed or apply-failed or abort-failed'
* result - 'success' or 'failed' or 'aborted'.
* reason and response - It's empty "" on success and on failure it's updated 
  with details of error.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the reason 
   for failure,if any."

**Note**

* Phase - This refers to 'create or apply or abort' phase of strategy
* Stage - This points to various stages at each phase.Example; 'sw-upgrade start deploy', 
  'sw-upgrade deploy host'
* Step - This refers to different steps executed in each stage. 
  Example; In 'sw-upgrade deploy host' stage, there are different steps like lock-hosts, 
  upgrade-hosts, system-stabilize, unlock-hosts.

When using this API to monitor the progress or status of a create, apply or abort
operation, wait for the 'completion-percentage' parameter to reach 100%.
The 'completion-percentage' is 100% only in success case.
Then, use the 'result' parameter to determine whether it indicates
'success' or 'failure'. In the failure scenario, the 'reason' and 'response'
parameters provide more detailed information related to the failure.

**Response body example**

::

          {
               "current-phase-completion": 100%
               "state": "ready-to-apply"
          }

Create phase is considered as completed if above values are set
in response message.

------------------------------
4) Apply sw-deploy-strategy
------------------------------

.. rest_method:: POST /api/orchestration/sw-upgrade/strategy/actions

**Request**

**Request body parameters**

.. csv-table::
           :header: "Parameter", "Style", "Type", "Description"
           :widths: 20, 20, 20, 60

           "action", "plain", "xsd:string", "The action to take: ``apply-all``, ``apply-stage``,
           ``abort`` or ``abort-stage``."
           "stage-id (Optional)", "plain", "xsd:string", "The stage-id to apply or abort.
           Only used with ``apply-stage`` or ``abort-stage`` actions."

**Note**

* stage-id - This is used to apply or abort a particular stage in the execution flow.
  Each stage has a number specified. This can be identified from the response parameter 
  'stage-id' which can be used to apply or abort a specific stage.
* apply-all or abort-all - This is recommended option, as it takes care of applying 
  or aborting all the required stages."

**Request body example**

::

           {
             "action": "apply-all"
           }

**Response**

**Normal response codes**

202

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Response parameters**

The "sw-deploy" strategy "apply" or "abort" request starts the apply or abort process, 
and returns a response to indicate the current status of the apply or abort process. 
E.g. typically after initially starting the create.

* state = 'applying' or 'aborting'.
* current-phase ='apply' or 'abort'

Use the sw-deploy get strategy request to monitor the progress and status of Apply strategy.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the reason 
   for failure,if any."

**Response body example**

::

            {
              "strategy": {
              "controller-apply-type": "serial",
              "current-phase-completion-percentage": 0,
              "uuid": "ac9b953a-caf1-4abe-8d53-498b598e6731",
              "name": "sw-upgrade",
              "worker-apply-type": "serial",
              "max-parallel-worker-hosts": 2,
              "current-phase": "apply",
              "apply-phase": {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "phase-name": "apply",
              "completion-percentage": 0,
              "total-stages": 3,
              "stop-at-stage": 3,
              "result": "inprogress",
              "timeout": 18304,
              "reason": "",
              "inprogress": true,
              "stages": [
              {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "stage-id": 0,
              "reason": "",
              "current-step": 0,
              "steps": [
              {
              "start-date-time": "2017-01-10 16:19:12",
              "end-date-time": "",
              "timeout": 60,
              "entity-type": "",
              "step-id": 0,
              "entity-uuids": [],
              "step-name": "query-alarms",
              "result": "wait",
              "entity-names": [],
              "reason": ""
              }
             }
            }

----------------------------
5) Show sw-deploy-strategy
----------------------------

.. rest_method:: GET /api/orchestration/sw-upgrade/strategy

**Request**

This operation does not accept a request body.

**Response**

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

**Response parameters**

The details of the strategy can be checked using below response parameter.

* state - 'building or applying or aborting' or 'ready-to-apply or 
  'applied' or 'aborted' or 'build-failed or apply-failed or abort-failed'.
* result - 'success' or 'failed' or 'aborted'.
* reason and response - It's empty "" on success and on failure it's updated 
  with details of error.

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "name", "plain", "xsd:string", "The current strategy name."
   "release", "plain", "xsd:string", "The release identification name."
   "controller-apply-type", "plain", "xsd:string", "Apply type of controller host."
   "storage-apply-type", "plain", "xsd:string", "Apply type of storage host."
   "worker-apply-type", "plain", "xsd:string", "Apply type of worker host."
   "state", "plain", "xsd:string", "The current strategy state."
   "current-phase", "plain", "xsd:string", "The current ongoing phase."
   "stage-name", "plain", "xsd:string", "The current stage of execution in the current phase."
   "step-name", "plain", "xsd:string", "The current step of execution in the current stage."
   "completion-percentage", "plain", "xsd:integer", "The completion percentage of strategy."
   "result", "plain", "xsd:string", "The result of current strategy."
   "reason", "plain", "xsd:string", "The reason for success/failure of the current phase."
   "response", "plain", "xsd:string", "This displays the detailed error message of the 
   reason for failure,if any."

**Note**

* Phase - This refers to 'create or apply or abort' phase of strategy
* Stage - This points to various stages at each phase.
  Example; 'sw-upgrade start deploy', 'sw-upgrade deploy host'
* Step - This refers to different steps executed in each stage. 
  Example; In 'sw-upgrade deploy host' stage, there are different steps like lock-hosts, 
  upgrade-hosts, system-stabilize, unlock-hosts.

When using this API to monitor the progress or status of a create, apply or abort
operation, wait for the 'completion-percentage' parameter to reach 100%.
The 'completion-percentage' is 100% only in success case.
Then, use the 'result' parameter to determine whether it indicates
'success' or 'failure'. In the failure scenario, the 'reason' and 'response'
parameters provide more detailed information related to the failure.

**Response body example**

::

            {
               "strategy": {
                  "current-phase-completion": "100%",
                  "state": "applied",
                }
            }

The apply phase is considered to be completed if above values are set.

**Note**
Software deployment delete will be performed by default as part of rollback orchestration.

------------------
6) Post-requisite
------------------

The typical port used for Software REST API is 5497.
The release should be rolled back and the earlier release would be marked
as the active one.

.. rest_method:: GET {software_url}:{software_port}/v1/release

**Request**

**Request body parameter**

.. csv-table::
       :header: "Parameter", "Style", "Type", "Description"
       :widths: 20, 20, 20, 60

       "release (Optional)", "query", "xsd:string", "Specifies the release to be queried."
       "show (Optional)", "query", "xsd:string", "Specifies the release state to be queried."

**Response**

**Normal response codes**

200

**Error response codes**

internalServerError (500)

**Response body example**

::

       [
         {
          "release_id":"stx-10.0.0",
          "state":"deployed",
          "sw_version":"10.0",
          "component":null,
          "status":"REL",
          "unremovable":true,
          "install_instructions":"",
          "warnings":"",
          "reboot_required": true,
        },
        {
          "release_id":"stx-10.0.1",
          "state":"deployed",
          "sw_version":"10.0",
          "component":null,
          "status":"REL",
          "unremovable":true,
          "install_instructions":"",
          "warnings":"",
          "reboot_required": true,
        }

       ]

stx-10.0.1 is rolled back
The system is healthy with no alarms.
