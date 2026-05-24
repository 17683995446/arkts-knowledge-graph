/**
 * 循环导入链 2, 文件 1
 */

import { Class2 } from './CircularChain2_2';

export class Class1 {
    use2() {
        return new Class2();
    }
}
