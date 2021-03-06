# Copyright 2017, Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from unittest.mock import Mock, call, patch

from tasks import _git, google_api_go_client
from tests import common

_REMOTE_URL = 'https://code.googlesource.com/_direct/google-api-go-client'


def _repository_mock_side_effect(repo_mock):
    def side_effect(filepath):
        repo_mock.filepath = filepath
        return repo_mock
    return side_effect


@patch('tasks.google_api_go_client.date')
@patch('tasks.google_api_go_client._git.Repository')
@patch('tasks.google_api_go_client.check_output')
@patch('tasks.google_api_go_client.os.environ')
def test_update(environ_mock, check_output_mock, repository_mock, date_mock):
    repo_mock = Mock()
    repo_mock.diff_name_status.return_value = [
        ('foo/v1/foo-api.json', _git.Status.ADDED),
        ('foo/v1/foo-gen.go', _git.Status.ADDED),
        ('bar/v1/bar-api.go', _git.Status.UPDATED),
        ('baz/v1/baz-api.go', _git.Status.DELETED),
        ('foobar/v1/foobar-api.json', _git.Status.UPDATED)
    ]
    environ_mock.copy.return_value = {}
    repository_mock.side_effect = _repository_mock_side_effect(repo_mock)
    date_mock.today.return_value.isoformat.return_value = '2000-01-01'

    manager = Mock()
    manager.attach_mock(check_output_mock, 'check_output')
    manager.attach_mock(repo_mock, 'repo')

    google_api_go_client.update('/tmp', common.GITHUB_ACCOUNT)
    assert manager.mock_calls == [
        call.check_output(
            ['go', 'get', '-d', '-t', 'google.golang.org/api/...'],
            env={'GOPATH': '/tmp'}),
        call.check_output(
            ['make', 'all'],
            cwd='/tmp/src/google.golang.org/api/google-api-go-generator',
            env={'GOPATH': '/tmp'}),
        call.repo.add(['.']),
        call.repo.diff_name_status(),
        call.check_output(['go', 'test', './...'],
                          cwd='/tmp/src/google.golang.org/api',
                          env={'GOPATH': '/tmp'}),
        call.repo.commit(('all: autogenerated update (2000-01-01)\n'
                          '\nAdd:\n- foo/v1\n'
                          '\nDelete:\n- baz/v1\n'
                          '\nUpdate:\n- bar/v1'),
                         'Alice',
                         'alice@test.com'),
        call.repo.push(remote=_REMOTE_URL, nokeycheck=True)
    ]


@patch('tasks.google_api_go_client._git.Repository')
@patch('tasks.google_api_go_client.check_output')
@patch('tasks.google_api_go_client.os.environ')
def test_update_no_changes(environ_mock, check_output_mock, repository_mock):
    repo_mock = Mock()
    repo_mock.diff_name_status.return_value = [
        ('foo/v1/foo-api.json', _git.Status.UPDATED)
    ]
    environ_mock.copy.return_value = {}
    repository_mock.side_effect = _repository_mock_side_effect(repo_mock)

    manager = Mock()
    manager.attach_mock(check_output_mock, 'check_output')
    manager.attach_mock(repo_mock, 'repo')

    google_api_go_client.update('/tmp', common.GITHUB_ACCOUNT)
    assert manager.mock_calls == [
        call.check_output(
            ['go', 'get', '-d', '-t', 'google.golang.org/api/...'],
            env={'GOPATH': '/tmp'}),
        call.check_output(
            ['make', 'all'],
            cwd='/tmp/src/google.golang.org/api/google-api-go-generator',
            env={'GOPATH': '/tmp'}),
        call.repo.add(['.']),
        call.repo.diff_name_status()
    ]
