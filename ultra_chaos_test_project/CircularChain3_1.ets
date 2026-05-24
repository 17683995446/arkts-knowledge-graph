/**
 * 循环导入链 3, 文件 1
 */

import { Class2 } from './CircularChain3_2';

export class Class1 {
    use2() {
        return new Class2();
    }
}
