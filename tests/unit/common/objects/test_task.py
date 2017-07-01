# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Tests for db.task layer."""

import datetime as dt

import ddt
import jsonschema
import mock

from rally.common import objects
from rally import consts
from rally import exceptions
from tests.unit import test


@ddt.ddt
class TaskTestCase(test.TestCase):
    def setUp(self):
        super(TaskTestCase, self).setUp()
        self.task = {
            "uuid": "00ef46a2-c5b8-4aea-a5ca-0f54a10cbca1",
            "status": consts.TaskStatus.INIT,
            "verification_log": "",
        }

    @mock.patch("rally.common.objects.task.db.task_create")
    def test_init_with_create(self, mock_task_create):
        mock_task_create.return_value = self.task
        task = objects.Task(status=consts.TaskStatus.CRASHED)
        mock_task_create.assert_called_once_with({
            "status": consts.TaskStatus.CRASHED})
        self.assertEqual(task["uuid"], self.task["uuid"])

    @mock.patch("rally.common.objects.task.db.task_create")
    def test_init_without_create(self, mock_task_create):
        task = objects.Task(task=self.task)
        self.assertFalse(mock_task_create.called)
        self.assertEqual(task["uuid"], self.task["uuid"])

    @mock.patch("rally.common.objects.task.uuid.uuid4",
                return_value="some_uuid")
    @mock.patch("rally.common.objects.task.db.task_create")
    def test_init_with_fake_true(self, mock_task_create, mock_uuid4):
        task = objects.Task(temporary=True)
        self.assertFalse(mock_task_create.called)
        self.assertTrue(mock_uuid4.called)
        self.assertEqual(task["uuid"], mock_uuid4.return_value)

    @mock.patch("rally.common.objects.task.db.task_get")
    def test_get(self, mock_task_get):
        mock_task_get.return_value = self.task
        task = objects.Task.get(self.task["uuid"])
        mock_task_get.assert_called_once_with(self.task["uuid"])
        self.assertEqual(task["uuid"], self.task["uuid"])

    @mock.patch("rally.common.objects.task.db.task_get_status")
    def test_get_status(self, mock_task_get_status):
        task = objects.Task(task=self.task)
        status = task.get_status(task["uuid"])
        self.assertEqual(status, mock_task_get_status.return_value)

    @mock.patch("rally.common.objects.task.db.task_delete")
    @mock.patch("rally.common.objects.task.db.task_create")
    def test_create_and_delete(self, mock_task_create, mock_task_delete):
        mock_task_create.return_value = self.task
        task = objects.Task()
        task.delete()
        mock_task_delete.assert_called_once_with(
            self.task["uuid"], status=None)

    @mock.patch("rally.common.objects.task.db.task_delete")
    @mock.patch("rally.common.objects.task.db.task_create")
    def test_create_and_delete_status(self, mock_task_create,
                                      mock_task_delete):
        mock_task_create.return_value = self.task
        task = objects.Task()
        task.delete(status=consts.TaskStatus.FINISHED)
        mock_task_delete.assert_called_once_with(
            self.task["uuid"], status=consts.TaskStatus.FINISHED)

    @mock.patch("rally.common.objects.task.db.task_delete")
    def test_delete_by_uuid(self, mock_task_delete):
        objects.Task.delete_by_uuid(self.task["uuid"])
        mock_task_delete.assert_called_once_with(
            self.task["uuid"], status=None)

    @mock.patch("rally.common.objects.task.db.task_delete")
    def test_delete_by_uuid_status(self, mock_task_delete):
        objects.Task.delete_by_uuid(self.task["uuid"],
                                    consts.TaskStatus.FINISHED)
        mock_task_delete.assert_called_once_with(
            self.task["uuid"], status=consts.TaskStatus.FINISHED)

    @mock.patch("rally.common.objects.task.db.task_list",
                return_value=[{"uuid": "a",
                               "created_at": "b",
                               "status": consts.TaskStatus.CRASHED,
                               "tag": "d",
                               "deployment_name": "some_name"}])
    def list(self, mock_db_task_list):
        tasks = objects.Task.list(status="somestatus")
        mock_db_task_list.assert_called_once_with("somestatus", None)
        self.assertIs(type(tasks), list)
        self.assertIsInstance(tasks[0], objects.Task)
        self.assertEqual(mock_db_task_list.return_value["uuis"],
                         tasks[0]["uuid"])

    @mock.patch("rally.common.objects.deploy.db.task_update")
    @mock.patch("rally.common.objects.task.db.task_create")
    def test_update(self, mock_task_create, mock_task_update):
        mock_task_create.return_value = self.task
        mock_task_update.return_value = {"opt": "val2"}
        deploy = objects.Task(opt="val1")
        deploy._update({"opt": "val2"})
        mock_task_update.assert_called_once_with(
            self.task["uuid"], {"opt": "val2"})
        self.assertEqual(deploy["opt"], "val2")

    @ddt.data(
        {
            "status": "some_status", "allowed_statuses": ("s_1", "s_2")
        },
        {
            "status": "some_status", "allowed_statuses": None
        }
    )
    @ddt.unpack
    @mock.patch("rally.common.objects.task.db.task_update_status")
    @mock.patch("rally.common.objects.task.db.task_update")
    def test_update_status(self, mock_task_update, mock_task_update_status,
                           status, allowed_statuses):
        task = objects.Task(task=self.task)
        task.update_status(consts.TaskStatus.FINISHED, allowed_statuses)
        if allowed_statuses:
            self.assertFalse(mock_task_update.called)
            mock_task_update_status.assert_called_once_with(
                self.task["uuid"],
                consts.TaskStatus.FINISHED,
                allowed_statuses
            )
        else:
            self.assertFalse(mock_task_update_status.called)
            mock_task_update.assert_called_once_with(
                self.task["uuid"],
                {"status": consts.TaskStatus.FINISHED},
            )

    @mock.patch("rally.common.objects.task.db.task_update")
    def test_update_verification_log(self, mock_task_update):
        mock_task_update.return_value = self.task
        task = objects.Task(task=self.task)
        task.set_validation_failed({"a": "fake"})
        mock_task_update.assert_called_once_with(
            self.task["uuid"],
            {"status": consts.TaskStatus.VALIDATION_FAILED,
             "validation_result": {"a": "fake"}}
        )

    @mock.patch("rally.common.objects.task.charts")
    def test_extend_results(self, mock_charts):
        self.assertRaises(TypeError, objects.Task.extend_results)

        mock_stat = mock.Mock()
        mock_stat.render.return_value = "durations_stat"
        mock_charts.MainStatsTable.return_value = mock_stat
        now = dt.datetime.now()
        iterations = [
            {"timestamp": i + 2, "duration": i + 5,
             "scenario_output": {"errors": "", "data": {}},
             "error": [], "idle_duration": i,
             "atomic_actions": [{"name": "keystone.create_user",
                                 "started_at": 0, "finished_at": i + 10},
                                {"name": "keystone.create_user",
                                 "started_at": 0, "finished_at": i + 11}
                                ]
             } for i in range(10)]
        obsolete = [
            {"task_uuid": "foo_uuid", "created_at": now, "updated_at": now,
             "id": 11, "key": {"kw": {"foo": 42},
                               "name": "Foo.bar", "pos": 0},
             "data": {"raw": iterations, "sla": [],
                      "hooks": [],
                      "full_duration": 40, "load_duration": 32}}]
        expected = [
            {"iterations": "foo_iterations", "sla": [],
             "hooks": [],
             "key": {"kw": {"foo": 42}, "name": "Foo.bar", "pos": 0},
             "info": {
                 "atomic": {"keystone.create_user": {"max_duration": 39,
                                                     "min_duration": 21,
                                                     "count": 2}},
                 "iterations_count": 10, "iterations_failed": 0,
                 "max_duration": 14, "min_duration": 5, "tstamp_start": 2,
                 "full_duration": 40, "load_duration": 32,
                 "stat": "durations_stat"}}]

        # serializable is default
        results = objects.Task.extend_results(obsolete)
        self.assertIsInstance(results[0]["iterations"], type(iter([])))
        self.assertEqual(list(results[0]["iterations"]), iterations)
        results[0]["iterations"] = "foo_iterations"
        expected[0]["created_at"] = now.strftime("%Y-%d-%m %H:%M:%S")
        expected[0]["updated_at"] = now.strftime("%Y-%d-%m %H:%M:%S")
        self.assertEqual(expected, results)

        # serializable is False
        results = objects.Task.extend_results(obsolete, serializable=False)
        self.assertIsInstance(results[0]["iterations"], type(iter([])))
        self.assertEqual(list(results[0]["iterations"]), iterations)
        results[0]["iterations"] = "foo_iterations"
        self.assertEqual(results, expected)

        # serializable is True
        results = objects.Task.extend_results(obsolete, serializable=True)
        self.assertEqual(list(results[0]["iterations"]), iterations)
        jsonschema.validate(results[0],
                            objects.task.TASK_EXTENDED_RESULT_SCHEMA)
        results[0]["iterations"] = "foo_iterations"
        self.assertEqual(results, expected)

    @mock.patch("rally.common.objects.task.db.deployment_get")
    @mock.patch("rally.common.objects.task.Task.get_results")
    def test_to_dict(self, mock_get_results, mock_deployment_get):
        results = [{"created_at": dt.datetime.now(),
                    "updated_at": dt.datetime.now()}]
        self.task.update({"deployment_uuid": "deployment_uuid",
                          "deployment_name": "deployment_name",
                          "created_at": dt.datetime.now(),
                          "updated_at": dt.datetime.now(),
                          "results": results})

        mock_get_results.return_value = results
        mock_deployment_get.return_value = {"name": "deployment_name"}

        task = objects.Task(task=self.task)
        serialized_task = task.to_dict()

        mock_get_results.assert_called_once_with()
        mock_deployment_get.assert_called_once_with(
            self.task["deployment_uuid"])
        self.assertEqual(self.task, serialized_task)

    @mock.patch("rally.common.db.api.task_get_detailed")
    def test_get_detailed(self, mock_task_get_detailed):
        task = objects.Task(task=self.task)
        mock_task_get_detailed.return_value = {"results": [{
            "created_at": dt.datetime.now(),
            "updated_at": dt.datetime.now()}]}

        task_detailed = task.get_detailed(task_id="task_id")
        mock_task_get_detailed.assert_called_once_with("task_id")
        self.assertEqual(mock_task_get_detailed.return_value, task_detailed)

    @mock.patch("rally.common.objects.task.db.task_result_get_all_by_uuid",
                return_value="foo_results")
    def test_get_results(self, mock_task_result_get_all_by_uuid):
        task = objects.Task(task=self.task)
        results = task.get_results()
        mock_task_result_get_all_by_uuid.assert_called_once_with(
            self.task["uuid"])
        self.assertEqual(results, "foo_results")

    @mock.patch("rally.common.objects.task.db.task_update")
    def test_set_failed(self, mock_task_update):
        mock_task_update.return_value = self.task
        task = objects.Task(task=self.task)
        task.set_failed("foo_type", "foo_error_message", "foo_trace")
        mock_task_update.assert_called_once_with(
            self.task["uuid"],
            {"status": consts.TaskStatus.CRASHED,
             "validation_result": {"etype": "foo_type",
                                   "msg": "foo_error_message",
                                   "trace": "foo_trace"}},
        )

    @mock.patch("rally.common.objects.task.Subtask")
    def test_add_subtask(self, mock_subtask):
        task = objects.Task(task=self.task)
        subtask = task.add_subtask(title="foo")
        mock_subtask.assert_called_once_with(
            self.task["uuid"], title="foo")
        self.assertIs(subtask, mock_subtask.return_value)

    @ddt.data(
        {
            "soft": True, "status": consts.TaskStatus.INIT
        },
        {
            "soft": True, "status": consts.TaskStatus.VALIDATING,
            "soft": True, "status": consts.TaskStatus.ABORTED
        },
        {
            "soft": True, "status": consts.TaskStatus.FINISHED
        },
        {
            "soft": True, "status": consts.TaskStatus.CRASHED
        },
        {
            "soft": False, "status": consts.TaskStatus.ABORTED
        },
        {
            "soft": False, "status": consts.TaskStatus.FINISHED
        },
        {
            "soft": False, "status": consts.TaskStatus.CRASHED
        }
    )
    @ddt.unpack
    def test_abort_with_finished_states(self, soft, status):
        task = objects.Task(mock.MagicMock(), fake=True)
        task.get_status = mock.MagicMock(return_value=status)
        task.update_status = mock.MagicMock()

        self.assertRaises(exceptions.RallyException, task.abort, soft)

        self.assertEqual(1, task.get_status.call_count)
        self.assertFalse(task.update_status.called)

    @ddt.data(True, False)
    def test_abort_with_running_state(self, soft):
        task = objects.Task(mock.MagicMock(), fake=True)
        task.get_status = mock.MagicMock(return_value="running")
        task.update_status = mock.MagicMock()

        task.abort(soft)
        if soft:
            status = consts.TaskStatus.SOFT_ABORTING
        else:
            status = consts.TaskStatus.ABORTING

        task.update_status.assert_called_once_with(
            status,
            allowed_statuses=(consts.TaskStatus.RUNNING,
                              consts.TaskStatus.SOFT_ABORTING)
        )


class SubtaskTestCase(test.TestCase):

    def setUp(self):
        super(SubtaskTestCase, self).setUp()
        self.subtask = {
            "task_uuid": "00ef46a2-c5b8-4aea-a5ca-0f54a10cbca1",
            "uuid": "00ef46a2-c5b8-4aea-a5ca-0f54a10cbca2",
            "title": "foo",
        }

    @mock.patch("rally.common.objects.task.db.subtask_create")
    def test_init(self, mock_subtask_create):
        mock_subtask_create.return_value = self.subtask
        subtask = objects.Subtask("bar", title="foo")
        mock_subtask_create.assert_called_once_with(
            "bar", title="foo")
        self.assertEqual(subtask["uuid"], self.subtask["uuid"])

    @mock.patch("rally.common.objects.task.db.subtask_update")
    @mock.patch("rally.common.objects.task.db.subtask_create")
    def test_update_status(self, mock_subtask_create, mock_subtask_update):
        mock_subtask_create.return_value = self.subtask
        subtask = objects.Subtask("bar", title="foo")
        subtask.update_status(consts.SubtaskStatus.FINISHED)
        mock_subtask_update.assert_called_once_with(
            self.subtask["uuid"], {"status": consts.SubtaskStatus.FINISHED})

    @mock.patch("rally.common.objects.task.Workload")
    @mock.patch("rally.common.objects.task.db.subtask_create")
    def test_add_workload(self, mock_subtask_create, mock_workload):
        mock_subtask_create.return_value = self.subtask
        subtask = objects.Subtask("bar", title="foo")

        workload = subtask.add_workload({"bar": "baz"})
        mock_workload.assert_called_once_with(
            self.subtask["task_uuid"], self.subtask["uuid"], {"bar": "baz"})
        self.assertIs(workload, mock_workload.return_value)


class WorkloadTestCase(test.TestCase):

    def setUp(self):
        super(WorkloadTestCase, self).setUp()
        self.workload = {
            "task_uuid": "00ef46a2-c5b8-4aea-a5ca-0f54a10cbca1",
            "subtask_uuid": "00ef46a2-c5b8-4aea-a5ca-0f54a10cbca2",
            "uuid": "00ef46a2-c5b8-4aea-a5ca-0f54a10cbca3",
        }

    @mock.patch("rally.common.objects.task.db.workload_create")
    def test_init(self, mock_workload_create):
        mock_workload_create.return_value = self.workload
        workload = objects.Workload("uuid1", "uuid2", {"bar": "baz"})
        mock_workload_create.assert_called_once_with(
            "uuid1", "uuid2", {"bar": "baz"})
        self.assertEqual(workload["uuid"], self.workload["uuid"])

    @mock.patch("rally.common.objects.task.db.workload_data_create")
    @mock.patch("rally.common.objects.task.db.workload_create")
    def test_add_workload_data(self, mock_workload_create,
                               mock_workload_data_create):
        mock_workload_create.return_value = self.workload
        workload = objects.Workload("uuid1", "uuid2", {"bar": "baz"})

        workload = workload.add_workload_data(0, {"data": "foo"})
        mock_workload_data_create.assert_called_once_with(
            self.workload["task_uuid"], self.workload["uuid"],
            0, {"data": "foo"})

    @mock.patch("rally.common.objects.task.db.workload_set_results")
    @mock.patch("rally.common.objects.task.db.workload_create")
    def test_set_results(self, mock_workload_create,
                         mock_workload_set_results):
        mock_workload_create.return_value = self.workload
        workload = objects.Workload("uuid1", "uuid2", {"bar": "baz"})
        workload.set_results({"data": "foo"})
        mock_workload_set_results.assert_called_once_with(
            workload_uuid=self.workload["uuid"],
            subtask_uuid=self.workload["subtask_uuid"],
            task_uuid=self.workload["task_uuid"],
            data={"data": "foo"})
