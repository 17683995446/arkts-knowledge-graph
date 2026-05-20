
@Component
struct PageOne {
  build() {
    Column() {
      Text('Page 1')
        .onClick(() => this.handleClick())
    }
  }

  private handleClick(): void {
    console.info('PageOne clicked')
  }

  private navigate(): void {
    console.info('PageOne navigate')
  }
}

@Component
struct PageTwo {
  build() {
    Column() {
      Text('Page 2')
        .onClick(() => this.handleClick())
    }
  }

  private handleClick(): void {
    console.info('PageTwo clicked')
  }

  private navigate(): void {
    console.info('PageTwo navigate')
  }
}

@Component
struct PageThree {
  build() {
    Column() {
      Text('Page 3')
        .onClick(() => this.handleClick())
    }
  }

  private handleClick(): void {
    console.info('PageThree clicked')
  }

  private navigate(): void {
    console.info('PageThree navigate')
  }
}
