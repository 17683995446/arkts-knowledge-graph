
// Traditional class
class DataModel {
  private data: string = ''
  
  getData(): string {
    return this.data
  }
  
  setData(value: string): void {
    this.data = value
    this.validate()
  }
  
  private validate(): boolean {
    return this.data.length > 0
  }
}

// ArkUI struct component
@Component
struct DataView {
  @State model: DataModel = new DataModel()

  build() {
    Column() {
      Text(this.model.getData())
      Button('Update')
        .onClick(() => {
          this.model.setData('new value')
          this.refresh()
        })
    }
  }

  private refresh(): void {
    console.info('refreshed')
  }
}

// Standalone utility function
function formatDate(timestamp: number): string {
  const date = new Date(timestamp)
  return date.toISOString()
}

function debounce(fn: Function, delay: number): Function {
  let timer: number = 0
  return () => {
    clearTimeout(timer)
    timer = setTimeout(fn, delay)
  }
}
