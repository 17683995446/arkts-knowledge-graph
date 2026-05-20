
class DeepNested {
  execute(): void {
    this.step1()
  }
  
  private step1(): void {
    Promise.resolve().then(() => {
      Promise.resolve().then(() => {
        Promise.resolve().then(() => {
          Promise.resolve().then(() => {
            Promise.resolve().then(() => {
              this.finalStep()
            })
          })
        })
      })
    })
  }
  
  private finalStep(): void {
    console.info('done')
  }
}
