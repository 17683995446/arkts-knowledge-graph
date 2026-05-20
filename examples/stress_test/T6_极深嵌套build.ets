
@Component
struct DeepNestPage {
  @State level: number = 0

  build() {
    Navigation() {
      NavDestination() {
        Column() {
          Row() {
            Column() {
              Stack() {
                Column() {
                  Scroll() {
                    List() {
                      ListItem() {
                        Row() {
                          Column() {
                            Text('Deep nested item')
                              .onClick(() => this.handleTap())
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
      .title('Deep Nest')
    }
  }

  private handleTap(): void {
    this.level++
    this.logLevel()
  }

  private logLevel(): void {
    console.info('level: ' + this.level)
  }
}
