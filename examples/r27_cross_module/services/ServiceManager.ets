
import { Service0 } from './Service0'
import { Service1 } from './Service1'
import { Service2 } from './Service2'
import { Service3 } from './Service3'
import { Service4 } from './Service4'
import { Service5 } from './Service5'
import { Service6 } from './Service6'
import { Service7 } from './Service7'
import { Service8 } from './Service8'
import { Service9 } from './Service9'

export class ServiceManager {
  private s0: Service0 = new Service0()
  private s1: Service1 = new Service1()
  private s2: Service2 = new Service2()
  private s3: Service3 = new Service3()
  private s4: Service4 = new Service4()
  private s5: Service5 = new Service5()
  private s6: Service6 = new Service6()
  private s7: Service7 = new Service7()
  private s8: Service8 = new Service8()
  private s9: Service9 = new Service9()
  
  processAll(): void {
    this.s0.process()
    this.s1.process()
    this.s2.process()
    this.s3.process()
    this.s4.process()
    this.s5.process()
    this.s6.process()
    this.s7.process()
    this.s8.process()
    this.s9.process()
  }
}
