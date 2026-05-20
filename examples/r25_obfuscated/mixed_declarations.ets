
interface IHandler {
  handle(): void
}

type Callback = (data: string) => void

enum Status {
  Pending,
  Running,
  Completed
}

class BaseHandler implements IHandler {
  handle(): void {
    this.process()
  }
  
  private process(): void {}
}

struct FastHandler {
  private status: Status = Status.Pending
  
  handle(): void {
    this.status = Status.Running
  }
}
