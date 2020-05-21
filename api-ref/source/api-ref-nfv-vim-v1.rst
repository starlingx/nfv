====================================================
NFV VIM API v1
====================================================

Manage patch orchestration with the StarlingX NFV VIM API. This
includes creation, application and querying of patch strategies.

Manage upgrade orchestration with the StarlingX NFV VIM API. This
includes creation, application and querying of upgrade strategies.

The typical port used for the NFV VIM REST API is 4545. However, proper
technique would be to look up the nfv vim service endpoint in Keystone.

-------------
API versions
-------------

*******************************************
Lists information about all NFV VIM links
*******************************************

.. rest_method:: GET /

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

This operation does not accept a request body.

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
         "href": "http://192.168.204.2:4545/orchestration/sw-patch/",
         "rel": "sw-patch"
       },
       {
         "href": "http://192.168.204.2:4545/orchestration/sw-upgrade/",
         "rel": "sw-upgrade"
       },
       {
         "href": "http://192.168.204.2:4545/orchestration/fw-update/",
         "rel": "fw-update"
       }
     ]
   }

This operation does not accept a request body.

**********************************************************************
Lists information about all NFV VIM API orchestration sw-patch links
**********************************************************************

.. rest_method:: GET /api/orchestration/sw-patch

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

::

   {
     "id": "sw-patch",
     "links": [
       {
         "href": "http://192.168.204.2:4545/orchestration/sw-patch/",
         "rel": "self"
       },
       {
         "href": "http://192.168.204.2:4545/orchestration/sw-patch/strategy/",
         "rel": "strategy"
       }
     ]
   }

This operation does not accept a request body.

************************************************************************
Lists information about all NFV VIM API orchestration sw-upgrade links
************************************************************************

.. rest_method:: GET /api/orchestration/sw-upgrade

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

This operation does not accept a request body.

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

---------------
Patch Strategy
---------------

Patch orchestration is done with a patch orchestration strategy, or
plan, for the automated patching procedure which contains a number of
parameters for customizing the particular behavior of the patching
orchestration.

****************************************************************
Shows detailed information about the current sw-patch strategy
****************************************************************

.. rest_method:: GET /api/orchestration/sw-patch/strategy

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

::

   {
     "strategy": {
       "controller-apply-type": "serial",
       "current-phase-completion-percentage": 100,
       "uuid": "c1971c42-b494-4ff0-8abf-dbde17929972",
       "worker-apply-type": "serial",
       "max-parallel-worker-hosts": 2,
       "alarm-restrictions": "strict",
       "current-phase": "build",
       "apply-phase": {
         "start-date-time": "",
         "end-date-time": "",
         "phase-name": "apply",
         "completion-percentage": 100,
         "total-stages": 6,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
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
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
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
                 "step-name": "sw-patch-hosts",
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
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 5,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "initial",
             "timeout": 4621,
             "total-steps": 6,
             "inprogress": false,
             "stage-name": "sw-patch-controllers"
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
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
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
                 "step-name": "sw-patch-hosts",
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
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 5,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "initial",
             "timeout": 4621,
             "total-steps": 6,
             "inprogress": false,
             "stage-name": "sw-patch-controllers"
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
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "instances",
                 "step-id": 1,
                 "entity-uuids": [
                   "e5236dac-288f-4a1d-b1de-1c630aaa0df0"
                 ],
                 "step-name": "migrate-instances",
                 "result": "initial",
                 "entity-names": [
                   "cirros-image-with-volumes-1"
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
                   "9a0dd555-a73b-4e49-b8e0-9cefeb2fb636"
                 ],
                 "step-name": "lock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-3"
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
                   "9a0dd555-a73b-4e49-b8e0-9cefeb2fb636"
                 ],
                 "step-name": "sw-patch-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-3"
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
                   "9a0dd555-a73b-4e49-b8e0-9cefeb2fb636"
                 ],
                 "step-name": "unlock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-3"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 5,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "initial",
             "timeout": 4621,
             "total-steps": 6,
             "inprogress": false,
             "stage-name": "sw-patch-worker-hosts"
           },
           {
             "start-date-time": "",
             "end-date-time": "",
             "stage-id": 3,
             "reason": "",
             "current-step": 0,
             "steps": [
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "instances",
                 "step-id": 1,
                 "entity-uuids": [
                   "ab977908-b5a4-44f1-832b-d7ebcfa476f0",
                   "7da7e6c6-fe9a-400e-99e5-4940b9b372ad",
                   "936fe92e-e48c-46ad-a052-9cdaea6fe840"
                 ],
                 "step-name": "migrate-instances",
                 "result": "initial",
                 "entity-names": [
                   "cirros-ephemeral-swap-1",
                   "cirros-1",
                   "cirros-ephemeral-1"
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
                   "8fb371f2-fe1c-4325-a6f5-3487e33c9059"
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
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 3,
                 "entity-uuids": [
                   "8fb371f2-fe1c-4325-a6f5-3487e33c9059"
                 ],
                 "step-name": "sw-patch-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-0"
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
                   "8fb371f2-fe1c-4325-a6f5-3487e33c9059"
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
                 "entity-type": "",
                 "step-id": 5,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "initial",
             "timeout": 4621,
             "total-steps": 6,
             "inprogress": false,
             "stage-name": "sw-patch-worker-hosts"
           },
           {
             "start-date-time": "",
             "end-date-time": "",
             "stage-id": 4,
             "reason": "",
             "current-step": 0,
             "steps": [
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "instances",
                 "step-id": 1,
                 "entity-uuids": [
                   "f8c263c7-06c6-46f9-8c34-e2451e5ac8d5"
                 ],
                 "step-name": "migrate-instances",
                 "result": "initial",
                 "entity-names": [
                   "cirros-swap-1"
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
                   "14cfa022-a29f-488b-a1e3-0c2a8231b33a"
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
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 3,
                 "entity-uuids": [
                   "14cfa022-a29f-488b-a1e3-0c2a8231b33a"
                 ],
                 "step-name": "sw-patch-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-1"
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
                   "14cfa022-a29f-488b-a1e3-0c2a8231b33a"
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
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 5,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "initial",
             "timeout": 4621,
             "total-steps": 6,
             "inprogress": false,
             "stage-name": "sw-patch-worker-hosts"
           },
           {
             "start-date-time": "",
             "end-date-time": "",
             "stage-id": 5,
             "reason": "",
             "current-step": 0,
             "steps": [
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 900,
                 "entity-type": "instances",
                 "step-id": 1,
                 "entity-uuids": [
                   "25ad74e3-e4fe-4d1d-920a-7e1ecb38625b"
                 ],
                 "step-name": "migrate-instances",
                 "result": "initial",
                 "entity-names": [
                   "cirros-image-1"
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
                   "c4f93e44-241b-4230-b4b3-098c0a9949fb"
                 ],
                 "step-name": "lock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-2"
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
                   "c4f93e44-241b-4230-b4b3-098c0a9949fb"
                 ],
                 "step-name": "sw-patch-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-2"
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
                   "c4f93e44-241b-4230-b4b3-098c0a9949fb"
                 ],
                 "step-name": "unlock-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-2"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 5,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "initial",
             "timeout": 4621,
             "total-steps": 6,
             "inprogress": false,
             "stage-name": "sw-patch-worker-hosts"
           }
         ],
         "current-stage": 0
       },
       "storage-apply-type": "serial",
       "state": "ready-to-apply",
       "default-instance-action": "migrate",
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
         "start-date-time": "2016-11-16 13:36:27",
         "end-date-time": "2016-11-16 13:36:28",
         "phase-name": "build",
         "completion-percentage": 100,
         "total-stages": 1,
         "stop-at-stage": 1,
         "result": "success",
         "timeout": 182,
         "reason": "",
         "inprogress": false,
         "stages": [
           {
             "start-date-time": "2016-11-16 13:36:27",
             "end-date-time": "2016-11-16 13:36:28",
             "stage-id": 0,
             "reason": "",
             "current-step": 3,
             "steps": [
               {
                 "start-date-time": "2016-11-16 13:36:27",
                 "end-date-time": "2016-11-16 13:36:27",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "success",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "2016-11-16 13:36:27",
                 "end-date-time": "2016-11-16 13:36:28",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 1,
                 "entity-uuids": [],
                 "step-name": "query-sw-patches",
                 "result": "success",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "2016-11-16 13:36:28",
                 "end-date-time": "2016-11-16 13:36:28",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 2,
                 "entity-uuids": [],
                 "step-name": "query-sw-patch-hosts",
                 "result": "success",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "success",
             "timeout": 181,
             "total-steps": 3,
             "inprogress": false,
             "stage-name": "sw-patch-query"
           }
         ],
         "current-stage": 1
       },
       "swift-apply-type": "ignore"
     }
   }

This operation does not accept a request body.

*****************************
Creates a sw-patch strategy
*****************************

.. rest_method:: POST /api/orchestration/sw-patch/strategy

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Request parameters**

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "controller-apply-type", "plain", "xsd:string", "The apply type for controller hosts: ``serial`` or ``ignore``."
   "storage-apply-type", "plain", "xsd:string", "The apply type for storage hosts: ``serial``, ``parallel`` or ``ignore``."
   "worker-apply-type", "plain", "xsd:string", "The apply type for worker hosts: ``serial``, ``parallel`` or ``ignore``."
   "max-parallel-worker-hosts (Optional)", "plain", "xsd:integer", "The maximum number of worker hosts to patch in parallel; only applicable if ``worker-apply-type = parallel``. Default value is ``2``."
   "swift-apply-type", "plain", "xsd:string", "The apply type for swift hosts: ``serial``, ``parallel`` or ``ignore``."
   "default-instance-action", "plain", "xsd:string", "The default instance action: ``stop-start`` or ``migrate``."
   "alarm-restrictions (Optional)", "plain", "xsd:string", "The strictness of alarm checks: ``strict`` or ``relaxed``."

::

   {
     "controller-apply-type": "serial",
     "default-instance-action": "stop-start",
     "worker-apply-type": "serial",
     "storage-apply-type": "serial",
     "swift-apply-type": "ignore",
     "alarm-restrictions": "strict"
   }

::

   {
     "strategy": {
       "controller-apply-type": "serial",
       "current-phase-completion-percentage": 0,
       "uuid": "15dc4b63-ae5f-48ca-b76e-ec367ef817f5",
       "worker-apply-type": "serial",
       "max-parallel-worker-hosts": 2,
       "alarm-restrictions": "strict",
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
         "current-stage": 0
       },
       "storage-apply-type": "serial",
       "state": "building",
       "default-instance-action": "stop-start",
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
         "start-date-time": "2016-11-16 19:14:05",
         "end-date-time": "",
         "phase-name": "build",
         "completion-percentage": 0,
         "total-stages": 1,
         "stop-at-stage": 1,
         "result": "inprogress",
         "timeout": 182,
         "reason": "",
         "inprogress": true,
         "stages": [
           {
             "start-date-time": "2016-11-16 19:14:05",
             "end-date-time": "",
             "stage-id": 0,
             "reason": "",
             "current-step": 0,
             "steps": [
               {
                 "start-date-time": "2016-11-16 19:14:05",
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
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 1,
                 "entity-uuids": [],
                 "step-name": "query-sw-patches",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 2,
                 "entity-uuids": [],
                 "step-name": "query-sw-patch-hosts",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "inprogress",
             "timeout": 181,
             "total-steps": 3,
             "inprogress": true,
             "stage-name": "sw-patch-query"
           }
         ],
         "current-stage": 0
       },
       "swift-apply-type": "ignore"
     }
   }

***************************************
Deletes the current sw-patch strategy
***************************************

.. rest_method:: DELETE /api/orchestration/sw-patch/strategy

**Normal response codes**

204

::

   {
   }

***************************************
Applies or aborts a sw-patch strategy
***************************************

.. rest_method:: POST /api/orchestration/sw-patch/strategy/actions

**Normal response codes**

202

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Request parameters**

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "action", "plain", "xsd:string", "The action to take: ``apply-all``, ``apply-stage``, ``abort`` or ``abort-stage``."
   "stage-id (Optional)", "plain", "xsd:string", "The stage-id to apply or abort. Only used with ``apply-stage`` or ``abort-stage`` actions."

::

   {
     "action": "apply-all"
   }

::

   {
     "strategy": {
       "controller-apply-type": "serial",
       "current-phase-completion-percentage": 0,
       "uuid": "15dc4b63-ae5f-48ca-b76e-ec367ef817f5",
       "worker-apply-type": "serial",
       "max-parallel-worker-hosts": 2,
       "alarm-restrictions": "strict",
       "current-phase": "apply",
       "apply-phase": {
         "start-date-time": "2016-11-16 19:28:28",
         "end-date-time": "",
         "phase-name": "apply",
         "completion-percentage": 0,
         "total-stages": 5,
         "stop-at-stage": 5,
         "result": "inprogress",
         "timeout": 9606,
         "reason": "",
         "inprogress": true,
         "stages": [
           {
             "start-date-time": "2016-11-16 19:28:28",
             "end-date-time": "",
             "stage-id": 0,
             "reason": "",
             "current-step": 0,
             "steps": [
               {
                 "start-date-time": "2016-11-16 19:28:28",
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
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 1,
                 "entity-uuids": [
                   "0f3715c0-fecd-46e0-9cd0-4fbb31810393"
                 ],
                 "step-name": "sw-patch-hosts",
                 "result": "initial",
                 "entity-names": [
                   "controller-0"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 2,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "inprogress",
             "timeout": 1921,
             "total-steps": 3,
             "inprogress": true,
             "stage-name": "sw-patch-controllers"
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
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 1,
                 "entity-uuids": [
                   "9a0dd555-a73b-4e49-b8e0-9cefeb2fb636"
                 ],
                 "step-name": "sw-patch-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-3"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 2,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "initial",
             "timeout": 1921,
             "total-steps": 3,
             "inprogress": false,
             "stage-name": "sw-patch-worker-hosts"
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
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 1,
                 "entity-uuids": [
                   "8fb371f2-fe1c-4325-a6f5-3487e33c9059"
                 ],
                 "step-name": "sw-patch-hosts",
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
                 "entity-type": "",
                 "step-id": 2,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "initial",
             "timeout": 1921,
             "total-steps": 3,
             "inprogress": false,
             "stage-name": "sw-patch-worker-hosts"
           },
           {
             "start-date-time": "",
             "end-date-time": "",
             "stage-id": 3,
             "reason": "",
             "current-step": 0,
             "steps": [
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 1,
                 "entity-uuids": [
                   "14cfa022-a29f-488b-a1e3-0c2a8231b33a"
                 ],
                 "step-name": "sw-patch-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-1"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 2,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "initial",
             "timeout": 1921,
             "total-steps": 3,
             "inprogress": false,
             "stage-name": "sw-patch-worker-hosts"
           },
           {
             "start-date-time": "",
             "end-date-time": "",
             "stage-id": 4,
             "reason": "",
             "current-step": 0,
             "steps": [
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 1800,
                 "entity-type": "hosts",
                 "step-id": 1,
                 "entity-uuids": [
                   "c4f93e44-241b-4230-b4b3-098c0a9949fb"
                 ],
                 "step-name": "sw-patch-hosts",
                 "result": "initial",
                 "entity-names": [
                   "compute-2"
                 ],
                 "reason": ""
               },
               {
                 "start-date-time": "",
                 "end-date-time": "",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 2,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "initial",
             "timeout": 1921,
             "total-steps": 3,
             "inprogress": false,
             "stage-name": "sw-patch-worker-hosts"
           }
         ],
         "current-stage": 0
       },
       "storage-apply-type": "serial",
       "state": "applying",
       "default-instance-action": "stop-start",
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
         "start-date-time": "2016-11-16 19:14:05",
         "end-date-time": "2016-11-16 19:14:05",
         "phase-name": "build",
         "completion-percentage": 100,
         "total-stages": 1,
         "stop-at-stage": 1,
         "result": "success",
         "timeout": 182,
         "reason": "",
         "inprogress": false,
         "stages": [
           {
             "start-date-time": "2016-11-16 19:14:05",
             "end-date-time": "2016-11-16 19:14:05",
             "stage-id": 0,
             "reason": "",
             "current-step": 3,
             "steps": [
               {
                 "start-date-time": "2016-11-16 19:14:05",
                 "end-date-time": "2016-11-16 19:14:05",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "success",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "2016-11-16 19:14:05",
                 "end-date-time": "2016-11-16 19:14:05",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 1,
                 "entity-uuids": [],
                 "step-name": "query-sw-patches",
                 "result": "success",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "2016-11-16 19:14:05",
                 "end-date-time": "2016-11-16 19:14:05",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 2,
                 "entity-uuids": [],
                 "step-name": "query-sw-patch-hosts",
                 "result": "success",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "success",
             "timeout": 181,
             "total-steps": 3,
             "inprogress": false,
             "stage-name": "sw-patch-query"
           }
         ],
         "current-stage": 1
       },
       "swift-apply-type": "ignore"
     }
   }

-----------------
Upgrade Strategy
-----------------

Upgrade orchestration is done with an upgrade orchestration strategy, or
plan, for the automated upgrade procedure which contains a number of
parameters for customizing the particular behavior of the upgrade
orchestration.

******************************************************************
Shows detailed information about the current sw-upgrade strategy
******************************************************************

.. rest_method:: GET /api/orchestration/sw-upgrade/strategy

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413), itemNotFound (404)

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
         "total-stages": 3,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
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
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
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
                   "controller-0"
                 ],
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
                   "controller-0"
                 ],
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
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
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
                 "timeout": 1800,
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
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 3,
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
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 4,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
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
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
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
                 "timeout": 1800,
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
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 3,
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
                 "entity-type": "",
                 "step-id": 4,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
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
                 "start-date-time": "2017-01-10 15:23:12",
                 "end-date-time": "2017-01-10 15:23:12",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "success",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "2017-01-10 15:23:12",
                 "end-date-time": "2017-01-10 15:23:12",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 1,
                 "entity-uuids": [],
                 "step-name": "query-upgrade",
                 "result": "success",
                 "entity-names": [],
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

This operation does not accept a request body.

*******************************
Creates a sw-upgrade strategy
*******************************

.. rest_method:: POST /api/orchestration/sw-upgrade/strategy

**Normal response codes**

200

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Request parameters**

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "storage-apply-type", "plain", "xsd:string", "The apply type for storage hosts: ``serial``, ``parallel`` or ``ignore``."
   "worker-apply-type", "plain", "xsd:string", "The apply type for worker hosts: ``serial``, ``parallel`` or ``ignore``."
   "max-parallel-worker-hosts (Optional)", "plain", "xsd:integer", "The maximum number of worker hosts to upgrade in parallel; only applicable if ``worker-apply-type = parallel``. Default value is ``2``."
   "alarm-restrictions (Optional)", "plain", "xsd:string", "The strictness of alarm checks: ``strict`` or ``relaxed``."

::

   {
     "worker-apply-type": "serial",
     "storage-apply-type": "serial",
     "alarm-restrictions": "relaxed"
   }

::

   {
     "strategy": {
       "controller-apply-type": "serial",
       "current-phase-completion-percentage": 0,
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
         "total-stages": 0,
         "stop-at-stage": 0,
         "result": "initial",
         "timeout": 0,
         "reason": "",
         "inprogress": false,
         "stages": [],
         "current-stage": 0
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
         "start-date-time": "2017-01-10 15:23:12",
         "end-date-time": "",
         "phase-name": "build",
         "completion-percentage": 0,
         "total-stages": 1,
         "stop-at-stage": 1,
         "result": "inprogress",
         "timeout": 122,
         "reason": "",
         "inprogress": true,
         "stages": [
           {
             "start-date-time": "2017-01-10 15:23:12",
             "end-date-time": "",
             "stage-id": 0,
             "reason": "",
             "current-step": 0,
             "steps": [
               {
                 "start-date-time": "2017-01-10 15:23:12",
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
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 1,
                 "entity-uuids": [],
                 "step-name": "query-upgrade",
                 "result": "initial",
                 "entity-names": [],
                 "reason": ""
               }
             ],
             "result": "inprogress",
             "timeout": 121,
             "total-steps": 2,
             "inprogress": true,
             "stage-name": "sw-upgrade-query"
           }
         ],
         "current-stage": 0
       },
       "swift-apply-type": "ignore"
     }
   }

*****************************************
Deletes the current sw-upgrade strategy
*****************************************

.. rest_method:: DELETE /api/orchestration/sw-upgrade/strategy

**Normal response codes**

204

::

   {
   }

*****************************************
Applies or aborts a sw-upgrade strategy
*****************************************

.. rest_method:: POST /api/orchestration/sw-upgrade/strategy/actions

**Normal response codes**

202

**Error response codes**

serviceUnavailable (503), badRequest (400), unauthorized (401),
forbidden (403), badMethod (405), overLimit (413)

**Request parameters**

.. csv-table::
   :header: "Parameter", "Style", "Type", "Description"
   :widths: 20, 20, 20, 60

   "action", "plain", "xsd:string", "The action to take: ``apply-all``, ``apply-stage``, ``abort`` or ``abort-stage``."
   "stage-id (Optional)", "plain", "xsd:string", "The stage-id to apply or abort. Only used with ``apply-stage`` or ``abort-stage`` actions."

::

   {
     "action": "apply-all"
   }

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
                   "controller-0"
                 ],
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
                   "controller-0"
                 ],
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
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
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
                 "timeout": 1800,
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
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 3,
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
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 4,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
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
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "initial",
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
                 "timeout": 1800,
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
                 "timeout": 900,
                 "entity-type": "hosts",
                 "step-id": 3,
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
                 "entity-type": "",
                 "step-id": 4,
                 "entity-uuids": [],
                 "step-name": "system-stabilize",
                 "result": "initial",
                 "entity-names": [],
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
             "current-step": 2,
             "steps": [
               {
                 "start-date-time": "2017-01-10 15:23:12",
                 "end-date-time": "2017-01-10 15:23:12",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 0,
                 "entity-uuids": [],
                 "step-name": "query-alarms",
                 "result": "success",
                 "entity-names": [],
                 "reason": ""
               },
               {
                 "start-date-time": "2017-01-10 15:23:12",
                 "end-date-time": "2017-01-10 15:23:12",
                 "timeout": 60,
                 "entity-type": "",
                 "step-id": 1,
                 "entity-uuids": [],
                 "step-name": "query-upgrade",
                 "result": "success",
                 "entity-names": [],
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
   "worker-apply-type", "plain", "xsd:string", "The apply type for worker hosts: ``serial``, ``parallel`` or ``ignore``."
   "max-parallel-worker-hosts (Optional)", "plain", "xsd:integer", "The maximum number of worker hosts to patch in parallel; only applicable if ``worker-apply-type = parallel``. Default value is ``2``."
   "default-instance-action", "plain", "xsd:string", "The default instance action: ``stop-start`` or ``migrate``."
   "alarm-restrictions (Optional)", "plain", "xsd:string", "The strictness of alarm checks: ``strict`` or ``relaxed``."

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

   "action", "plain", "xsd:string", "The action to take: ``apply-all``, ``apply-stage``, ``abort`` or ``abort-stage``."
   "stage-id (Optional)", "plain", "xsd:string", "The stage-id to apply or abort. Only used with ``apply-stage`` or ``abort-stage`` actions."

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

