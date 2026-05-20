
class CallbackHell {
  fetchData(callback: Function): void {
    this.step1((result1: string) => {
      this.step2(result1, (result2: string) => {
        this.step3(result2, (result3: string) => {
          this.step4(result3, (result4: string) => {
            this.step5(result4, (result5: string) => {
              this.step6(result5, (result6: string) => {
                this.step7(result6, (result7: string) => {
                  callback(result7)
                })
              })
            })
          })
        })
      })
    })
  }
  
  private step1(cb: Function): void { cb('step1') }
  private step2(input: string, cb: Function): void { cb(input + 'step2') }
  private step3(input: string, cb: Function): void { cb(input + 'step3') }
  private step4(input: string, cb: Function): void { cb(input + 'step4') }
  private step5(input: string, cb: Function): void { cb(input + 'step5') }
  private step6(input: string, cb: Function): void { cb(input + 'step6') }
  private step7(input: string, cb: Function): void { cb(input + 'step7') }
}
