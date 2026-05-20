
// 基础按钮组件
@Component
export struct BaseButton {
  @Prop label: string = ''
  @Prop type: 'primary' | 'secondary' | 'danger' = 'primary'
  @Prop disabled: boolean = false
  private onClick: () => void = () => {}
  
  build() {
    Button(this.label)
      .enabled(!this.disabled)
      .onClick(() => this.onClick())
  }
}

// 基础输入组件
@Component
export struct BaseInput {
  @Prop placeholder: string = ''
  @Prop type: 'text' | 'password' | 'number' = 'text'
  @Link value: string
  @Prop maxLength: number = 100
  
  build() {
    TextInput({ placeholder: this.placeholder, text: this.value })
      .type(this.type === 'password' ? InputType.Password : InputType.Normal)
      .maxLength(this.maxLength)
      .onChange((v) => this.value = v)
  }
}

// 基础卡片组件
@Component
export struct BaseCard {
  @Prop title: string = ''
  @Prop elevation: number = 2
  @BuilderParam content: () => void
  
  build() {
    Column() {
      Text(this.title)
      this.content()
    }
    .shadow({ radius: this.elevation })
  }
}

// 基础列表组件
@Component
export struct BaseList<T> {
  @Prop items: T[] = []
  @BuilderParam itemBuilder: (item: T, index: number) => void
  
  build() {
    List() {
      ForEach(this.items, (item: T, index: number) => {
        ListItem() {
          this.itemBuilder(item, index)
        }
      })
    }
  }
}
