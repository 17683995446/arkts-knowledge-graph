
import { Logger as UtilLogger } from './utils/Logger'
import { Logger as ServiceLogger } from './services/Logger'

export class App {
  private utilLogger: UtilLogger = new UtilLogger()
  private serviceLogger: ServiceLogger = new ServiceLogger()
  
  init(): void {
    this.utilLogger.setPrefix('App')
    this.serviceLogger.setLevel('DEBUG')
  }
  
  run(): void {
    this.utilLogger.log('Starting app')
    this.serviceLogger.log('App running')
  }
}
