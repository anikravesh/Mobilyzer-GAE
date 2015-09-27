# Copyright 2012 Google Inc.
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
#!/usr/bin/python2.4
#

"""Configuration options for the Mobiperf service."""

__author__ = 'drchoffnes@gmail.com (David Choffnes)'

# Set of users with admin privileges
ADMIN_USERS = ['drchoffnes@gmail.com', 'haneul0318@gmail.com', 'sanae@umich.edu', 'ashnik@umich.edu', 'zmao@umich.edu', 'morley@gmail.com', 'Sanae.Rosen@gmail.com']
ADMIN_ANONYMOUS_USERS = ADMIN_USERS
ADMIN_ANONYMOUS_USERS.append('huangshu91@gmail.com')

# Set of users with rights to administer tasks
SCHEDULE_ADMIN_USERS = ['drchoffnes@gmail.com', 'haneul0318@gmail.com', 'sanae@umich.edu' , 'ashnik@umich.edu', 'zmao@umich.edu' , 'morley@gmail.com', 'Sanae.Rosen@gmail.com']

VALIDATION_EMAIL_SENDER = 'David Choffnes <drchoffnes@gmail.com>'
VALIDATION_EMAIL_RECIPIENT = 'David Choffnes <drchoffnes@gmail.com>'

# Archive Settings
ARCHIVE_GS_BUCKET = 'openmobiledata'
ARCHIVE_GS_ACL = 'project-private'

# local salt
IMEI_SALT = 'vzS6lRNEj9yf8XErdTayF2IY7nV4u7DGkgpP56ij80I'
