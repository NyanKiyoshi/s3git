class BaseError(Exception):
    MSG = ''

    def __init__(self, frmt):
        self.msg = self.MSG % frmt
        super().__init__(self.msg)


class ConfigurationError(BaseError):
    pass


class MissingConfigurationFile(ConfigurationError):
    MSG = 'Cannot find the configuration file: %s'


class MissingSectionConfigurationFile(ConfigurationError):
    MSG = '%s is missing an usable section'


class RequiredValueMissingInConfigurationFile(ConfigurationError):
    MSG = '%s is missing the required option %s'


class RepoError(BaseError):
    pass


class InvalidRepository(RepoError):
    MSG = 'The current working directory (%s) does not contain ' \
          'a valid git repository.'


class RemoteUpToDate(RepoError):
    MSG = 'Remote repository is up to date.'


class UnexpectedDiffStatus(RepoError):
    MSG = 'The program received an unexpected diff status (%s) from git. ' \
          'This may be a bug, please report it to us.'
