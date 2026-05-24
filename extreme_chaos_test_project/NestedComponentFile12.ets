/**
 * 嵌套组件文件 - 深度 12
 */

import { NestedComponent13 } from './NestedComponentFile13';

@Component
export struct NestedComponent12 {

    build() {
        Column() {
            NestedComponent13()
            NestedComponent13()
            NestedComponent13()
        }
    }

}
