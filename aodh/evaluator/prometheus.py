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
import datetime
import requests

from oslo_log import log

from gnocchiclient import exceptions
from aodh.evaluator import threshold
from aodh import keystone_client

LOG = log.getLogger(__name__)

GRANULARITY = 1
VALUE = 2


class PrometheusBase(threshold.ThresholdEvaluator):
    def __init__(self, conf):
        super(PrometheusBase, self).__init__(conf)
        LOG.debug("in constructor")
        self._prometheus_client = None

    @staticmethod
    def _sanitize(rule, statistics):
        """Return the datapoints that correspond to the alarm granularity"""
        # TODO(sileht): if there's no direct match, but there is an archive
        # policy with granularity that's an even divisor or the period,
        # we could potentially do a mean-of-means (or max-of-maxes or whatever,
        # but not a stddev-of-stddevs).
        # TODO(sileht): support alarm['exclude_outliers']
        LOG.debug('sanitize stats %s', statistics)
        # NOTE(jamespage)
        # Dynamic Aggregates are returned in a dict struct so
        # check for this first.
        if isinstance(statistics, dict):
            # Pop array of measures from aggregated subdict
            statistics = statistics['measures']['aggregated']
        statistics = [stats[VALUE] for stats in statistics
                      if stats[GRANULARITY] == rule['granularity']]
        if not statistics:
            raise threshold.InsufficientDataError(
                "No datapoint for granularity %s" % rule['granularity'], [])
        statistics = statistics[-rule['evaluation_periods']:]
        LOG.debug('pruned statistics to %d', len(statistics))
        return statistics


class PrometheusEvaluator(PrometheusBase):
    def _statistics(self, rule, start, end):
        try:
            #curl "localhost:9090/api/v1/query" --data-urlencode 'query=ceilometer_volume_size{resource="fc43cfb9-00e2-41fc-a6c7-3e416a5fbb54"}'
            if rule['aggregation_method'] == "mean":
                rule['aggregation_method'] = "avg"
#            range = round(datetime.fromisoformat(end).timestamp()) - round(datetime.fromisoformat(start).timestamp())

            LOG.debug("http://localhost:9090/api/v1/query %s" % {
                'query': rule['aggregation_method'] + '(ceilometer_' + str(rule['metric']).replace(".", "_") + '{resource="' + rule['resource_id'] + '"})',

                })

            ret = requests.get('http://localhost:9090/api/v1/query', params={
                'query': rule['aggregation_method'] + '(ceilometer_' + str(rule['metric']).replace(".", "_") + '{resource="' + rule['resource_id'] + '"})',
#                'time': round(datetime.fromisoformat(end).timestamp())

                })
            

            LOG.debug(ret)
            LOG.debug(ret.content)
            query_result = json.loads(ret.content)
            result_list = []
            for res in query_result["data"]["result"]:
                result_list.append((datetime.datetime.fromtimestamp(res["value"][0], tz=datetime.timezone(datetime.timedelta(0), '+00:00')), rule['granularity'], float(res["value"][1])))
            LOG.debug(result_list)
            return result_list

        # Some (not working) ideas about incorporating the start, end and granularity values
#            ret = requests.get('http://localhost:9090/api/v1/query_range', params={
#                'query': rule['aggregation_method'] + '(ceilometer_' + str(rule['metric']).replace(".", "_") + '{resource="' + rule['resource_id'] + '"}' + ')',
#                'start': round(datetime.fromisoformat(start).timestamp()), 'end': round(datetime.fromisoformat(end).timestamp()),
#                'step': rule['granularity'],
#
#                })
            # add the "end - start" into [] after the metric name, so that the query looks something like: query=ceilometer_volume_size{resource="smth"}[300s]
#            ret = requests.get('http://localhost:9090/api/v1/query', params={
#                'query': rule['aggregation_method'] + '(ceilometer_' + str(rule['metric']).replace(".", "_") + '{resource="' + rule['resource_id'] + '"})',
#                'time': round(datetime.fromisoformat(end).timestamp())

#                })
        except exceptions.MetricNotFound:
            raise threshold.InsufficientDataError(
                'metric %s for resource %s does not exists' %
                (rule['metric'], rule['resource_id']), [])
        except exceptions.ResourceNotFound:
            raise threshold.InsufficientDataError(
                'resource %s does not exists' % rule['resource_id'], [])
        except exceptions.NotFound:
            # TODO(sileht): gnocchiclient should raise a explicit
            # exception for AggregationNotFound, this API endpoint
            # can only raise 3 different 404, so we are safe to
            # assume this is an AggregationNotFound for now.
            raise threshold.InsufficientDataError(
                'aggregation %s does not exist for '
                'metric %s of resource %s' % (rule['aggregation_method'],
                                              rule['metric'],
                                              rule['resource_id']),
                [])
        except Exception as e:
            msg = 'alarm statistics retrieval failed: %s' % e
            LOG.warning(msg)
            raise threshold.InsufficientDataError(msg, [])


