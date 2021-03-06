# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

import os
import textwrap

from twitter.common.confluence import Confluence, ConfluenceError

from pants import binary_util
from pants.backend.core.targets.doc import Page
from pants.backend.core.tasks.task import Task
from pants.base.exceptions import TaskError
from pants.util.dirutil import safe_open


"""Classes to ease publishing Page targets to Confluence wikis."""

class ConfluencePublish(Task):

  @classmethod
  def register_options(cls, register):
    super(ConfluencePublish, cls).register_options(register)
    register('--url',
             help='The url of the confluence site to post to.',
             legacy='confluence_publish_url')
    register('--force',
             action='store_true',
             default=False,
             help=('Force publish the page even if its contents is '
                   'identical to the contents on confluence.'),
             legacy='confluence_publish_force')
    register('--open',
             action='store_true',
             default=False,
             help=('Attempt to open the published confluence wiki page '
                   'in a browser.'),
             legacy='confluence_publish_open')
    register('--user',
             help='Confluence user name, defaults to unix user.',
             legacy='confluence_user')

  def __init__(self, *args, **kwargs):
    super(ConfluencePublish, self).__init__(*args, **kwargs)

    self.url = (
      self.context.options.confluence_publish_url
      or self.context.config.get('confluence-publish', 'url')
    )

    if not self.url:
      raise TaskError("Unable to proceed publishing to confluence. Please configure a 'url' under "
                      "the 'confluence-publish' heading in pants.ini or using the %s command line "
                      "option." % self.url_option)

    self.force = self.context.options.confluence_publish_force
    self.open = self.context.options.confluence_publish_open
    self._wiki = None
    self.user = self.context.options.confluence_user

  def prepare(self, round_manager):
    round_manager.require('wiki_html')

  def wiki(self):
    raise NotImplementedError('Subclasses must provide the wiki target they are associated with')

  def api(self):
    return 'confluence1'

  def execute(self):
    pages = []
    targets = self.context.targets()
    for target in targets:
      if isinstance(target, Page):
        for wiki_artifact in target.payload.provides:
          pages.append((target, wiki_artifact))

    urls = list()

    genmap = self.context.products.get('wiki_html')
    for page, wiki_artifact in pages:
      html_info = genmap.get((wiki_artifact, page))
      if len(html_info) > 1:
        raise TaskError('Unexpected resources for %s: %s' % (page, html_info))
      basedir, htmls = html_info.items()[0]
      if len(htmls) != 1:
        raise TaskError('Unexpected resources for %s: %s' % (page, htmls))
      with safe_open(os.path.join(basedir, htmls[0])) as contents:
        url = self.publish_page(
          page.address,
          wiki_artifact.config['space'],
          wiki_artifact.config['title'],
          contents.read(),
          # Default to none if not present in the hash.
          parent=wiki_artifact.config.get('parent')
        )
        if url:
          urls.append(url)
          self.context.log.info('Published %s to %s' % (page, url))

    if self.open and urls:
      binary_util.ui_open(*urls)

  def publish_page(self, address, space, title, content, parent=None):
    body = textwrap.dedent('''

    <!-- DO NOT EDIT - generated by pants from %s -->

    %s
    ''').strip() % (address, content)

    pageopts = dict(
      versionComment = 'updated by pants!'
    )
    wiki = self.login()
    existing = wiki.getpage(space, title)
    if existing:
      if not self.force and existing['content'].strip() == body.strip():
        self.context.log.warn("Skipping publish of '%s' - no changes" % title)
        return

      pageopts['id'] = existing['id']
      pageopts['version'] = existing['version']

    try:
      page = wiki.create_html_page(space, title, body, parent, **pageopts)
      return page['url']
    except ConfluenceError as e:
      raise TaskError('Failed to update confluence: %s' % e)

  def login(self):
    if not self._wiki:
      try:
        self._wiki = Confluence.login(self.url, self.user, self.api())
      except ConfluenceError as e:
        raise TaskError('Failed to login to confluence: %s' % e)
    return self._wiki
