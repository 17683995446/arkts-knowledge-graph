
@Component
export struct Button {
  @Prop label: string = ''
  @Prop onClick: () => void = () => {}
  
  build() {
    Text(this.label)
  }
}
