
@Entry
@Component
struct LargePage {
  @State private data: string[] = []
  @State private loading: boolean = false
  @State private error: string = ''
  @State private page: number = 1
  @State private hasMore: boolean = true
  @State private selectedId: string = ''
  @State private showModal: boolean = false
  @State private modalContent: string = ''
  @State private searchQuery: string = ''
  @State private filterType: string = 'all'
  @State private sortBy: string = 'date'
  @State private sortOrder: 'asc' | 'desc' = 'desc'
  
  private pageSize: number = 20
  private totalCount: number = 0
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private async loadData(): Promise<void> {
    this.loading = true
    this.error = ''
    
    try {
      await this.fetchData()
      this.hasMore = this.data.length < this.totalCount
    } catch (e) {
      this.error = 'Failed to load data'
    } finally {
      this.loading = false
    }
  }
  
  private async fetchData(): Promise<void> {
    // Simulate API call
    for (let i = 0; i < this.pageSize; i++) {
      this.data.push(`Item ${this.data.length + 1}`)
    }
    this.totalCount = 100
  }
  
  private async loadMore(): Promise<void> {
    if (!this.hasMore || this.loading) return
    this.page++
    await this.loadData()
  }
  
  private async refresh(): Promise<void> {
    this.page = 1
    this.data = []
    await this.loadData()
  }
  
  private handleSearch(query: string): void {
    this.searchQuery = query
    this.refresh()
  }
  
  private handleFilter(type: string): void {
    this.filterType = type
    this.refresh()
  }
  
  private handleSort(by: string): void {
    if (this.sortBy === by) {
      this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc'
    } else {
      this.sortBy = by
      this.sortOrder = 'desc'
    }
    this.refresh()
  }
  
  private handleItemClick(id: string): void {
    this.selectedId = id
    this.showModal = true
    this.modalContent = `Details for ${id}`
  }
  
  private closeModal(): void {
    this.showModal = false
    this.selectedId = ''
    this.modalContent = ''
  }
  
  private deleteItem(id: string): void {
    this.data = this.data.filter(item => item !== id)
  }
  
  private editItem(id: string): void {
    // Open edit modal
    this.showModal = true
    this.modalContent = `Edit ${id}`
  }
  
  private shareItem(id: string): void {
    // Share functionality
    console.info(`Sharing ${id}`)
  }
  
  private exportData(): void {
    console.info('Exporting data...')
  }
  
  private importData(): void {
    console.info('Importing data...')
  }
  
  private resetFilters(): void {
    this.searchQuery = ''
    this.filterType = 'all'
    this.sortBy = 'date'
    this.sortOrder = 'desc'
    this.refresh()
  }
  
  build() {
    Column() {
      // Search bar
      Row() {
        TextInput({ placeholder: 'Search...' })
          .onChange((v) => this.handleSearch(v))
      }
      
      // Filter buttons
      Row() {
        Button('All').onClick(() => this.handleFilter('all'))
        Button('Active').onClick(() => this.handleFilter('active'))
        Button('Inactive').onClick(() => this.handleFilter('inactive'))
      }
      
      // Sort buttons
      Row() {
        Button('Sort by Date').onClick(() => this.handleSort('date'))
        Button('Sort by Name').onClick(() => this.handleSort('name'))
      }
      
      // Data list
      if (this.loading) {
        Text('Loading...')
      } else if (this.error) {
        Text(this.error)
      } else {
        List() {
          ForEach(this.data, (item: string) => {
            ListItem() {
              Row() {
                Text(item)
                Button('Edit').onClick(() => this.editItem(item))
                Button('Delete').onClick(() => this.deleteItem(item))
                Button('Share').onClick(() => this.shareItem(item))
              }
            }
          })
        }
        .onReachEnd(() => this.loadMore())
      }
      
      // Action buttons
      Row() {
        Button('Refresh').onClick(() => this.refresh())
        Button('Export').onClick(() => this.exportData())
        Button('Import').onClick(() => this.importData())
        Button('Reset').onClick(() => this.resetFilters())
      }
    }
  }
}
