
import { router } from '@kit.ArkUI'
import { http } from '@kit.NetworkKit'

@Entry
@Component
struct HomePage {
  @State message: string = 'Hello'
  @State count: number = 0

  aboutToAppear(): void {
    this.loadData()
  }

  build() {
    Column() {
      Text(this.message)
        .fontSize(24)
      Button('Next')
        .onClick(() => {
          this.increment()
          this.navigate()
        })
      HeaderComp({ title: 'Home' })
      ContentArea()
      FooterComp()
    }
  }

  private increment(): void {
    this.count++
    this.logCount()
  }

  private logCount(): void {
    console.info('count: ' + this.count)
  }

  private navigate(): void {
    router.pushUrl({ url: 'pages/Detail' })
  }

  private async loadData(): Promise<void> {
    const res = await http.request('https://api.example.com/data')
    this.message = res.result as string
  }
}

@Component
struct HeaderComp {
  @Prop title: string = ''

  build() {
    Row() {
      Text(this.title)
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
      BadgeComp({ count: 5 })
    }
    .width('100%')
    .padding(16)
  }
}

@Component
struct ContentArea {
  @State items: string[] = []

  aboutToAppear(): void {
    this.fetchItems()
  }

  build() {
    List() {
      ForEach(this.items, (item: string) => {
        ListItem() {
          Text(item)
        }
      })
    }
  }

  private async fetchItems(): Promise<void> {
    this.items = ['Item1', 'Item2', 'Item3']
  }
}

@Component
struct FooterComp {
  build() {
    Row() {
      Text('Footer')
        .fontSize(12)
    }
    .justifyContent(FlexAlign.Center)
  }
}

@Component
struct BadgeComp {
  @Prop count: number = 0

  build() {
    if (this.count > 0) {
      Text(this.count.toString())
        .fontSize(10)
    }
  }
}
