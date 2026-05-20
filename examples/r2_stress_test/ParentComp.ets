
@Component
struct ParentComp {
  build() {
    Column() {
      ChildA()
      ChildB()
    }
  }
}

@Component
struct ChildA {
  build() {
    Text('A')
  }
}
