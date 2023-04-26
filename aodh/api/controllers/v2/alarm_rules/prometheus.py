#
# Copyright 2023 Red Hat, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import json
import threading

import cachetools
from keystoneauth1 import exceptions as ka_exceptions
from oslo_config import cfg
from oslo_log import log
import pecan
import wsme
from wsme import types as wtypes

from aodh.api.controllers.v2 import base
from aodh.api.controllers.v2 import utils as v2_utils
from aodh import keystone_client

LOG = log.getLogger(__name__)

class PrometheusRule(base.AlarmRule):
    comparison_operator = base.AdvEnum('comparison_operator', str,
                                       'lt', 'le', 'eq', 'ne', 'ge', 'gt',
                                       default='eq')
    "The comparison against the alarm threshold"

    threshold = wsme.wsattr(float, mandatory=True)
    "The threshold of the alarm"

    aggregation_method = wsme.wsattr(wtypes.text, mandatory=True)
    "The aggregation_method to compare to the threshold"

    evaluation_periods = wsme.wsattr(wtypes.IntegerType(minimum=1), default=1)
    "The number of historical periods to evaluate the threshold"

    granularity = wsme.wsattr(wtypes.IntegerType(minimum=1), default=60)
    "The time range in seconds over which query"

    metric = wsme.wsattr(wtypes.text, mandatory=True)
    "The name of the metric"

    resource_id = wsme.wsattr(wtypes.text, mandatory=True)
    "The id of a resource"

    resource_type = wsme.wsattr(wtypes.text, mandatory=True)
    "The resource type"

    @staticmethod
    def validate(threshold_rule):
        return threshold_rule


    def as_dict(self):
        rule = self.as_dict_from_keys(['granularity', 'comparison_operator',
                                       'threshold', 'aggregation_method',
                                       'evaluation_periods',
                                       'metric',
                                       'resource_id',
                                       'resource_type'])
        return rule
