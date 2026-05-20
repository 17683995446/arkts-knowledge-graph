
class Orchestrator {
  private validator: Validator = new Validator()
  private transformer: Transformer = new Transformer()
  private persister: Persister = new Persister()
  private notifier: Notifier = new Notifier()
  private logger: Logger = new Logger()

  execute(): void {
    this.validate()
    this.transform()
    this.persist()
    this.notify()
    this.log()
    this.cleanup()
  }

  private validate(): void {
    this.validator.check()
    this.validator.sanitize()
  }

  private transform(): void {
    this.transformer.convert()
    this.transformer.optimize()
    this.transformer.compress()
  }

  private persist(): void {
    this.persister.save()
    this.persister.backup()
  }

  private notify(): void {
    this.notifier.send()
    this.notifier.log()
  }

  private log(): void {
    this.logger.info()
    this.logger.debug()
    this.logger.warn()
  }

  private cleanup(): void {
    console.info('cleanup done')
  }
}

class Validator {
  check(): void {}
  sanitize(): void {}
}

class Transformer {
  convert(): void {}
  optimize(): void {}
  compress(): void {}
}

class Persister {
  save(): void {}
  backup(): void {}
}

class Notifier {
  send(): void {}
  log(): void {}
}

class Logger {
  info(): void {}
  debug(): void {}
  warn(): void {}
}
