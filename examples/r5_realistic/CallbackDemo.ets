
class CallbackDemo {
  private items: string[] = []

  processItems(callback: (item: string) => void): void {
    for (let i = 0; i < this.items.length; i++) {
      callback(this.items[i])
    }
  }

  transformItems(transform: (item: string) => string): void {
    this.items = this.items.map(transform)
  }

  private filterItems(): void {
    this.items = this.items.filter((item: string) => item.length > 0)
  }

  execute(): void {
    this.processItems((item: string) => {
      console.info(item)
    })
    this.filterItems()
  }
}
