
import { router } from '@kit.ArkUI'
import { http } from '@kit.NetworkKit'

@Entry
@Component
struct RealPage {
  @State pageTitle: string = 'Loading...'
  @State dataList: string[] = []
  @State isLoading: boolean = false
  @Provide currentPage: number = 1

  aboutToAppear(): void {
    this.loadPageData()
  }

  onPageShow(): void {
    console.info('page show')
  }

  onPageHide(): void {
    console.info('page hide')
  }

  build() {
    Navigation() {
      Column() {
        Text(this.pageTitle)
          .fontSize(24)
          .fontWeight(FontWeight.Bold)

        if (this.isLoading) {
          LoadingProgress()
            .width(40)
            .height(40)
        } else {
          List() {
            ForEach(this.dataList, (item: string) => {
              ListItem() {
                Text(item)
                  .onClick(() => this.handleItemClick(item))
              }
            })
          }
        }

        Row() {
          Button('Prev')
            .onClick(() => this.prevPage())
          Button('Next')
            .onClick(() => this.nextPage())
        }
        .width('100%')
        .justifyContent(FlexAlign.SpaceEvenly)
      }
    }
    .title('Real Page Demo')
  }

  private async loadPageData(): Promise<void> {
    this.isLoading = true
    try {
      const res = await http.request('https://api.example.com/data?page=' + this.currentPage)
      const data = JSON.parse(res.result as string)
      this.dataList = data.items as string[]
      this.pageTitle = data.title as string
    } catch (err) {
      this.pageTitle = 'Error: ' + err.message
    } finally {
      this.isLoading = false
    }
  }

  private handleItemClick(item: string): void {
    router.pushUrl({ url: 'pages/Detail', params: { item: item } })
  }

  private prevPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--
      this.loadPageData()
    }
  }

  private nextPage(): void {
    this.currentPage++
    this.loadPageData()
  }
}
