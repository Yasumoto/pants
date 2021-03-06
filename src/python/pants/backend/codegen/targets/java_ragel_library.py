# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from pants.backend.jvm.targets.jvm_target import JvmTarget
from pants.base.build_manual import manual
from pants.base.config import Config
from pants.base.exceptions import TargetDefinitionException


class JavaRagelLibrary(JvmTarget):
  """Generates a stub Java library from a Ragel file."""

  def __init__(self, **kwargs):
    super(JavaRagelLibrary, self).__init__(**kwargs)

    self.add_labels('codegen')
