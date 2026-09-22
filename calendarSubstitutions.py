"""Apply user-configured aliases to CEWE calendar resources."""

import logging


def applyCalendarSubstitutions(resources, definitions, resourceType):
    """Alias newline-separated ``source, replacement`` definitions.

    Calendar schemas and layouts use the same INI syntax.  Keeping the parser
    here makes their validation and diagnostics consistent.
    """
    substitutedResources = dict(resources)
    for definition in definitions.splitlines():
        if not definition.strip():
            continue
        sourceAndTarget = [part.strip() for part in definition.split(',', 1)]
        if len(sourceAndTarget) != 2 or not all(sourceAndTarget):
            logging.warning('Ignoring invalid calendar %s substitution: %r',
                            resourceType, definition)
            continue
        source, target = sourceAndTarget
        replacement = resources.get(target)
        if replacement is None:
            logging.warning(
                'Calendar %s substitution %r cannot use missing %s %r',
                resourceType, source, resourceType, target)
            continue
        substitutedResources[source] = replacement
        logging.info('Using calendar %s %s in place of %s',
                     resourceType, target, source)
    return substitutedResources
