
type State = 'idle' | 'loading' | 'success' | 'error'

class StateMachine {
  private _state: State = 'idle'
  private _listeners: ((state: State) => void)[] = []
  
  get state(): State {
    return this._state
  }
  
  transition(event: string): void {
    switch (this._state) {
      case 'idle':
        if (event === 'START') {
          this.setState('loading')
        }
        break
      case 'loading':
        if (event === 'SUCCESS') {
          this.setState('success')
        } else if (event === 'FAIL') {
          this.setState('error')
        }
        break
      case 'success':
      case 'error':
        if (event === 'RESET') {
          this.setState('idle')
        }
        break
    }
  }
  
  subscribe(listener: (state: State) => void): () => void {
    this._listeners.push(listener)
    return () => {
      this._listeners = this._listeners.filter(l => l !== listener)
    }
  }
  
  private setState(newState: State): void {
    this._state = newState
    this.notify()
  }
  
  private notify(): void {
    this._listeners.forEach(l => l(this._state))
  }
}
